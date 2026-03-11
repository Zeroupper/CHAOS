"""Evaluation metrics: accuracy, consistency, Cohen's d."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

import numpy as np
from pydantic import BaseModel

if TYPE_CHECKING:
    from chaos.llm.structured_client import StructuredLLMClient


# --- Answer extraction ---


class _ExtractedValue(BaseModel):
    """LLM-extracted numeric answer."""
    value: float | None = None


_EXTRACT_SYSTEM = (
    "Extract the numeric answer to the query from the given text. "
    "Return the value as a number, or null if the text does not contain a clear answer. "
    "Do not compute or infer — only extract what is explicitly stated."
)


def extract_answer_for_query(
    query: str,
    answer: str | None,
    llm_client: StructuredLLMClient,
) -> float | None:
    """Use a fast LLM call to extract the numeric answer from free text."""
    if answer is None:
        return None

    stripped = answer.strip()
    if stripped.lower().startswith("cannot complete"):
        return None

    # Fast path: answer is already just a number
    number_re = r"-?\d[\d,]*(?:\.\d+)?"
    if re.fullmatch(number_re, stripped):
        return float(stripped.replace(",", ""))

    result = llm_client.chat(
        messages=[{
            "role": "user",
            "content": f"Query: {query}\n\nAnswer text: {answer}\n\nWhat is the numeric answer?",
        }],
        response_model=_ExtractedValue,
        system=_EXTRACT_SYSTEM,
    )
    return result.value


# --- Accuracy ---


def check_accuracy(predicted: float | None, expected: float | None) -> bool:
    """Check if predicted matches expected within 0.5% relative tolerance."""
    if predicted is None or expected is None:
        return False
    return _within_tolerance(predicted, expected)


def relative_error(
    predicted: float | None,
    expected: float | None,
) -> float | None:
    """Compute relative error: |predicted - expected| / |expected|.

    Returns None if either value is None or expected is zero.
    A return value of 0.0 means exact match, 0.01 means 1% off, etc.
    """
    if predicted is None or expected is None:
        return None
    try:
        p, e = float(predicted), float(expected)
        if e == 0:
            return 0.0 if p == 0 else None
        return abs(p - e) / abs(e)
    except (ValueError, TypeError):
        return None


# --- Consistency ---


def _within_tolerance(a: float, b: float, rel_tol: float = 0.005) -> bool:
    return abs(a - b) <= abs(b) * rel_tol


def consistency_score(answers: list[float | None]) -> float:
    """Fraction of answers matching the most frequent value (0.5% tolerance).

    Example: [24, 42, 12, 12] → 2/4 = 0.50 (12 is most frequent).
    None values (extraction failures) cluster into a single group.
    """
    if not answers:
        return 0.0

    groups: dict[float | None, int] = {}
    for val in answers:
        if val is None:
            groups[None] = groups.get(None, 0) + 1
            continue
        for rep in groups:
            if rep is not None and _within_tolerance(val, rep):
                groups[rep] += 1
                break
        else:
            groups[val] = 1

    return max(groups.values()) / len(answers)


# --- Cohen's d ---


def cohens_d(group1: list[float], group2: list[float]) -> float | None:
    """Compute Cohen's d effect size between two groups.

    d = (mean1 - mean2) / pooled_std

    Interpretation:
    - |d| < 0.2: negligible
    - 0.2 <= |d| < 0.5: small
    - 0.5 <= |d| < 0.8: medium
    - |d| >= 0.8: large
    """
    if len(group1) < 2 or len(group2) < 2:
        return None

    n1, n2 = len(group1), len(group2)
    mean1, mean2 = np.mean(group1), np.mean(group2)
    var1, var2 = np.var(group1, ddof=1), np.var(group2, ddof=1)

    # Pooled standard deviation
    pooled_std = np.sqrt(((n1 - 1) * var1 + (n2 - 1) * var2) / (n1 + n2 - 2))

    if pooled_std == 0:
        return 0.0

    return float((mean1 - mean2) / pooled_std)
