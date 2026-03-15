"""Pydantic models and data types for the evaluation framework."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, Field


# --- Test case types ---


@dataclass
class RubricCriterion:
    """Single criterion in a subjective rubric."""

    criterion: str
    weight: float
    description: str


@dataclass
class TestCase:
    """A single evaluation test case with optional rubric."""

    id: str
    category: str  # "objective" | "subjective"
    difficulty: str  # "simple" | "medium" | "complex"
    query: str
    hint: str = ""

    # Subjective fields
    rubric: list[RubricCriterion] = field(default_factory=list)


# --- LLM-as-judge response models ---


class CriterionScore(BaseModel):
    """Score for a single rubric criterion from the judge."""

    criterion: str
    score: float = Field(ge=0.0, le=1.0)
    reasoning: str


class SubjectiveEvaluation(BaseModel):
    """Complete subjective evaluation from the judge."""

    criteria_scores: list[CriterionScore]
    overall_score: float = Field(ge=0.0, le=1.0)
    faithfulness_score: float = Field(ge=0.0, le=1.0)
    faithfulness_reasoning: str = ""
    unsupported_claims: list[str] = Field(default_factory=list)
    summary: str


class FaithfulnessScore(BaseModel):
    """Faithfulness assessment: are claims supported by execution evidence?"""

    score: float = Field(ge=0.0, le=1.0)
    unsupported_claims: list[str] = Field(default_factory=list)
    reasoning: str


# --- Subjective result (typed replacement for dict[str, Any]) ---


@dataclass
class SubjectiveResult:
    """Typed result from subjective LLM-as-judge evaluation."""

    overall_score: float
    faithfulness_score: float
    criteria_scores: list[dict[str, Any]]
    summary: str
    faithfulness_reasoning: str = ""
    unsupported_claims: list[str] = field(default_factory=list)


# --- Evaluation result types ---


@dataclass
class RunMetrics:
    """Metrics collected from a single run."""

    total_tokens: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    duration_seconds: float = 0.0
    code_executions: int = 0
    code_successes: int = 0


@dataclass
class EvalResult:
    """Result from evaluating a single test case in one run."""

    case_id: str
    config_name: str
    repeat_index: int
    answer: str | None = None
    extracted_value: float | None = None

    # Objective metrics
    is_correct: bool | None = None
    relative_error: float | None = None

    # Subjective metrics
    subjective_eval: SubjectiveResult | None = None

    # Execution metrics
    metrics: RunMetrics = field(default_factory=RunMetrics)

    # Execution evidence (full orchestrator state entries)
    execution_evidence: list[dict[str, Any]] = field(default_factory=list)

    # Sensemaker run log entries (reasoning, requests, reviews)
    run_log_entries: list[dict[str, Any]] = field(default_factory=list)

    # Raw pipeline output
    raw_result: dict[str, Any] = field(default_factory=dict)

    # Path to exported run markdown file
    export_path: str | None = None

    # Error info
    error: str | None = None


def strip_heavy_fields(results: list[EvalResult]) -> None:
    """Drop bulky evidence/log data from results to free memory.

    Call this after subjective evaluation is done — the heavy fields are only
    needed by the judge for faithfulness scoring.  The per-run markdown exports
    (via export_path) already contain the full evidence.
    """
    for r in results:
        r.execution_evidence.clear()
        r.run_log_entries.clear()
        r.raw_result.clear()


@dataclass
class AggregateMetrics:
    """Aggregated metrics across multiple runs for a config+case."""

    accuracy: float | None = None
    avg_relative_error: float | None = None
    consistency: float | None = None
    avg_rubric_score: float | None = None
    avg_faithfulness: float | None = None
    code_success_rate: float | None = None
    avg_tokens: float | None = None
    avg_latency: float | None = None  # avg wall-clock seconds per run
    cohens_d: float | None = None

    # Per-difficulty breakdowns
    accuracy_by_difficulty: dict[str, float] = field(default_factory=dict)
    rubric_by_difficulty: dict[str, float] = field(default_factory=dict)
