"""Evaluation metrics: accuracy, consistency, Cohen's d."""

from __future__ import annotations

import re

import numpy as np


# --- Answer extraction ---


def _parse_number(s: str) -> float:
    """Parse a number string, stripping commas. '11,157' -> 11157.0"""
    return float(s.replace(",", ""))


# Matches numbers like: 155, 155.0, -1.5, 11,157, 14,005.0
_NUMBER = r"-?\d[\d,]*(?:\.\d+)?"


def extract_numeric(answer: str | None) -> float | None:
    """Extract the primary numeric value from a free-text answer.

    Tries to parse the answer as a plain number first, then falls back to
    result-indicator patterns (e.g. "is 155.0"), then to the last number.
    Skips answers that indicate failure.
    """
    if answer is None:
        return None

    stripped = answer.strip()

    # Skip error/failure answers — no valid numeric result to extract
    if stripped.lower().startswith("cannot complete"):
        return None

    # Best case: answer is just a number (e.g. "155.0", "-1.5", "11,157")
    if re.fullmatch(_NUMBER, stripped):
        return _parse_number(stripped)

    # Prefer numbers after result indicators like "is", "was", ":", "="
    match = re.search(
        rf"(?:is|was|equals?|=|:)\s*({_NUMBER})", answer, re.IGNORECASE
    )
    if match:
        return _parse_number(match.group(1))

    # Fallback: last number in the text (most likely the final answer)
    numbers = re.findall(_NUMBER, answer)
    if numbers:
        return _parse_number(numbers[-1])

    return None


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
