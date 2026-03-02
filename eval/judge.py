"""LLM-as-judge for subjective rubric scoring and faithfulness evaluation."""

from __future__ import annotations

from typing import Any

from chaos.core.config import LLMConfig
from chaos.llm.structured_client import StructuredLLMClient

from .types import CriterionScore, EvalResult, FaithfulnessScore, SubjectiveEvaluation, TestCase

CRITERION_SYSTEM = """\
You are an expert evaluator assessing the quality of a data analysis system's work.

You will be given the original query, the full execution context (plan, reasoning,
code executed, results obtained), and the final answer.

Evaluate the ENTIRE analysis process — not just the final answer text.
If the system gathered good data and reasoned well during execution but produced
a terse final answer, credit the analytical work.

Score strictly between 0.0 and 1.0:
- 0.0: Completely fails  - 0.5: Partially meets  - 1.0: Fully meets

Provide reasoning in 1-2 sentences maximum.
"""

FAITHFULNESS_SYSTEM = """\
You are an expert evaluator assessing whether an answer is faithful to the
execution evidence (code that was run and results obtained).

Check if ALL factual claims in the answer are supported by execution evidence.
Look for: numeric values not in any result, statistical claims not backed by
computation, conclusions drawn from data never queried.

Score between 0.0 (completely unfaithful) and 1.0 (fully faithful).
Provide reasoning in 1-2 sentences. List only unsupported claims, if any.
"""


class JudgeAgent:
    def __init__(self, judge_model: str) -> None:
        self._client = StructuredLLMClient(LLMConfig(model=judge_model))

    def judge_result(self, r: EvalResult, case: TestCase) -> SubjectiveEvaluation:
        """Score a subjective result: rubric criteria + faithfulness."""
        context = self._format_context(r)

        # Score each rubric criterion
        criteria_scores = [
            self._client.chat(
                messages=[{"role": "user", "content": (
                    f"Query: {case.query}\n\nFinal Answer: {r.answer}\n\n"
                    f"{context}\n\n"
                    f"Score 0-1 for criterion: '{rc.criterion}'\n"
                    f"Description: {rc.description}"
                )}],
                response_model=CriterionScore,
                system=CRITERION_SYSTEM,
            )
            for rc in case.rubric
        ]

        # Weighted overall score
        total_weight = sum(rc.weight for rc in case.rubric)
        overall = (
            sum(cs.score * rc.weight for cs, rc in zip(criteria_scores, case.rubric))
            / total_weight
            if total_weight > 0
            else 0.0
        )

        # Faithfulness check
        faithfulness = FaithfulnessScore(score=0.0, reasoning="No evidence", unsupported_claims=[])
        if r.execution_evidence:
            faithfulness = self._client.chat(
                messages=[{"role": "user", "content": (
                    f"Query: {case.query}\n\nAnswer: {r.answer}\n\n"
                    f"Execution Evidence:\n{self._format_evidence(r.execution_evidence)}\n\n"
                    "Check if all factual claims are supported. Score 0-1."
                )}],
                response_model=FaithfulnessScore,
                system=FAITHFULNESS_SYSTEM,
            )

        return SubjectiveEvaluation(
            criteria_scores=criteria_scores,
            overall_score=round(overall, 3),
            faithfulness_score=round(faithfulness.score, 3),
            faithfulness_reasoning=faithfulness.reasoning,
            unsupported_claims=faithfulness.unsupported_claims,
            summary=f"Rubric: {overall:.2f} | Faithfulness: {faithfulness.score:.2f}",
        )

    def _format_context(self, r: EvalResult) -> str:
        """Format plan + run log + evidence into a single context string."""
        parts: list[str] = []

        plan = r.raw_result.get("plan") if r.raw_result else None
        if plan:
            steps = "\n".join(
                f"  Step {s.get('step', '?')}: {s.get('action', '')} [source: {s.get('source', '-')}]"
                for s in plan.get("steps", [])
            )
            parts.append(f"## Plan\n{plan.get('query_understanding', '')}\n{steps}")

        if r.run_log_entries:
            log_lines = []
            for e in r.run_log_entries:
                src, action, content = e.get("source", ""), e.get("action", ""), e.get("content", {})
                if src == "sensemaker" and action == "request":
                    log_lines.append(f"Request: {content.get('request', '')}")
                elif src == "info_seeker" and action == "response":
                    code = content.get("params", {}).get("code", "")
                    if code:
                        log_lines.append(f"Code:\n```python\n{code}\n```")
                    log_lines.append(f"Result: {str(content.get('results', ''))[:1000]}")
            if log_lines:
                parts.append("## Execution Log\n" + "\n".join(log_lines))
        elif r.execution_evidence:
            parts.append("## Evidence\n" + self._format_evidence(r.execution_evidence))

        return "\n\n".join(parts)

    def _format_evidence(self, entries: list[dict[str, Any]]) -> str:
        lines = []
        for e in entries:
            step = e.get("step", "?")
            if e.get("is_internal_context"):
                lines.append(f"Step {step} (context): {str(e.get('result', ''))[:500]}")
            else:
                code = e.get("code", "")
                if code:
                    lines.append(f"Step {step} code:\n```python\n{code}\n```")
                if e.get("success"):
                    lines.append(f"Step {step} result: {str(e.get('result', ''))[:1000]}")
                else:
                    lines.append(f"Step {step} error: {e.get('error', 'unknown')}")
        return "\n".join(lines)
