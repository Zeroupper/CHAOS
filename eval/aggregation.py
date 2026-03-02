"""Metric computation and aggregation for evaluation results."""

from __future__ import annotations

from collections import defaultdict

from .metrics import cohens_d, consistency_score
from .types import AggregateMetrics, EvalResult, TestCase


def compute_aggregates(
    results: list[EvalResult],
    cases: list[TestCase],
    rag_config_name: str | None = None,
) -> dict[str, AggregateMetrics]:
    """Compute one AggregateMetrics per model config."""
    case_map = {c.id: c for c in cases}

    by_config: dict[str, list[EvalResult]] = defaultdict(list)
    for r in results:
        by_config[r.config_name].append(r)

    aggregates = {
        name: _aggregate(config_results, case_map)
        for name, config_results in by_config.items()
    }

    # Cohen's d: each non-RAG config vs RAG baseline
    if rag_config_name and rag_config_name in aggregates:
        rag_scores = _obj_scores(by_config[rag_config_name], case_map)
        for name, agg in aggregates.items():
            if name != rag_config_name:
                agg.cohens_d = cohens_d(
                    _obj_scores(by_config[name], case_map), rag_scores
                )

    return aggregates


def _aggregate(
    results: list[EvalResult],
    case_map: dict[str, TestCase],
) -> AggregateMetrics:
    """Aggregate all runs for one model config."""
    agg = AggregateMetrics()

    by_case: dict[str, list[EvalResult]] = defaultdict(list)
    for r in results:
        if r.case_id in case_map:
            by_case[r.case_id].append(r)

    # --- Objective metrics ---
    correctness: list[float] = []          # 1.0/0.0 per run
    rel_errors: list[float] = []           # per run
    correctness_by_diff: dict[str, list[float]] = defaultdict(list)
    case_consistencies: list[float] = []

    for case_id, runs in by_case.items():
        case = case_map[case_id]
        if case.category != "objective":
            continue
        for r in runs:
            # None means extraction failed — count as wrong, not skip
            correct = 1.0 if r.is_correct else 0.0
            correctness.append(correct)
            correctness_by_diff[case.difficulty].append(correct)
            if r.relative_error is not None:
                rel_errors.append(r.relative_error)
        case_consistencies.append(
            consistency_score([r.extracted_value for r in runs])
        )

    if correctness:
        agg.accuracy = sum(correctness) / len(correctness)
    if rel_errors:
        agg.avg_relative_error = sum(rel_errors) / len(rel_errors)
    if case_consistencies:
        agg.consistency = sum(case_consistencies) / len(case_consistencies)
    for diff, scores in correctness_by_diff.items():
        agg.accuracy_by_difficulty[diff] = sum(scores) / len(scores)

    # --- Subjective metrics ---
    rubric_scores: list[float] = []        # per run
    faithfulness_scores: list[float] = []  # per run
    rubric_by_diff: dict[str, list[float]] = defaultdict(list)

    for case_id, runs in by_case.items():
        case = case_map[case_id]
        if case.category != "subjective":
            continue
        for r in runs:
            if not r.subjective_eval:
                continue
            rubric_scores.append(r.subjective_eval.overall_score)
            rubric_by_diff[case.difficulty].append(r.subjective_eval.overall_score)
            faithfulness_scores.append(r.subjective_eval.faithfulness_score)

    if rubric_scores:
        agg.avg_rubric_score = sum(rubric_scores) / len(rubric_scores)
    if faithfulness_scores:
        agg.avg_faithfulness = sum(faithfulness_scores) / len(faithfulness_scores)
    for diff, scores in rubric_by_diff.items():
        agg.rubric_by_difficulty[diff] = sum(scores) / len(scores)

    # --- Execution metrics ---
    total_code_runs = sum(r.metrics.code_executions for r in results)
    total_code_ok = sum(r.metrics.code_successes for r in results)
    if total_code_runs > 0:
        agg.code_success_rate = total_code_ok / total_code_runs
    if results:
        agg.avg_tokens = sum(r.metrics.total_tokens for r in results) / len(results)
        agg.avg_latency = sum(r.metrics.duration_seconds for r in results) / len(results)

    return agg


def _obj_scores(
    results: list[EvalResult], case_map: dict[str, TestCase]
) -> list[float]:
    """Binary objective scores (1.0/0.0) for Cohen's d."""
    return [
        1.0 if r.is_correct else 0.0
        for r in results
        if (c := case_map.get(r.case_id))
        and c.category == "objective"
        and r.is_correct is not None
    ]
