"""Result evaluation: objective accuracy and subjective LLM-as-judge scoring."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import TYPE_CHECKING

from chaos.core.config import LLMConfig
from chaos.llm.structured_client import StructuredLLMClient

from .judge import JudgeAgent
from .metrics import check_accuracy, extract_answer_for_query, relative_error
from .types import SubjectiveResult

if TYPE_CHECKING:
    from .config import EvalConfig
    from .types import EvalResult, TestCase


_EXTRACT_MODEL = "openai/gpt-oss-20b:nitro"


def evaluate_objective_results(
    results: list[EvalResult],
    case_map: dict[str, TestCase],
    test_cases_path: str
) -> None:
    """Evaluate objective results in-place: extract numeric values and check accuracy."""
    from .test_cases import load_ground_truth

    ground_truth = load_ground_truth(test_cases_path)
    llm_client = StructuredLLMClient(LLMConfig(model=_EXTRACT_MODEL))

    for r in results:
        case = case_map.get(r.case_id)
        if not case or case.category != "objective":
            continue
        if case.id not in ground_truth:
            print(f"  Warning: no ground truth for {case.id}, skipping evaluation")
            continue
        expected = ground_truth[case.id][1]
        r.extracted_value = extract_answer_for_query(case.query, r.answer, llm_client)
        r.is_correct = check_accuracy(r.extracted_value, expected)
        r.relative_error = relative_error(r.extracted_value, expected)


def evaluate_subjective_results(
    results: list[EvalResult],
    case_map: dict[str, TestCase],
    eval_config: EvalConfig,
) -> None:
    """Run LLM-as-judge evaluation for subjective queries in parallel."""
    subjective_pairs = [
        (r, case_map[r.case_id])
        for r in results
        if r.case_id in case_map
        and case_map[r.case_id].category == "subjective"
        and r.answer
    ]
    if not subjective_pairs:
        return

    print(f"\nRunning LLM-as-judge evaluation ({len(subjective_pairs)} items, "
          f"max {eval_config.max_workers} workers)...")
    judge = JudgeAgent(eval_config.judge_model)

    max_judge_workers = min(eval_config.max_workers, len(subjective_pairs))
    with ThreadPoolExecutor(max_workers=max_judge_workers) as executor:
        futures = {
            executor.submit(judge.judge_result, r, case): r
            for r, case in subjective_pairs
        }
        for future in as_completed(futures):
            r = futures[future]
            try:
                evaluation = future.result()
                r.subjective_eval = SubjectiveResult(
                    overall_score=evaluation.overall_score,
                    faithfulness_score=evaluation.faithfulness_score,
                    criteria_scores=[
                        {"criterion": cs.criterion, "score": cs.score, "reasoning": cs.reasoning}
                        for cs in evaluation.criteria_scores
                    ],
                    summary=evaluation.summary,
                    faithfulness_reasoning=evaluation.faithfulness_reasoning,
                    unsupported_claims=evaluation.unsupported_claims,
                )
                print(f"  Judged {r.case_id} (run {r.repeat_index + 1}): {evaluation.overall_score:.2f}")
            except Exception as e:
                print(f"  Judge error for {r.case_id}: {e}")
