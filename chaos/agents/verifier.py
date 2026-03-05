"""Verifier agent - validates answers against the execution plan."""

from typing import Any

from ..core.config import Config
from ..core.logger import truncate_for_llm
from ..llm.structured_client import StructuredLLMClient
from ..types import ExplanationResponse, Plan, Verification
from .base import BaseAgent


class VerifierAgent(BaseAgent):
    """
    Verifies whether the sensemaker's answer matches the execution plan.

    Responsibilities:
    - Evaluate answer completeness against plan steps
    - Check answer accuracy
    - Identify gaps or issues
    - Generate human-readable report
    """

    def __init__(self, config: Config, llm_client: StructuredLLMClient) -> None:
        super().__init__(config, llm_client)
        self._system_prompt = """Verify an answer against its execution plan. The plan defines what should be computed.

RULES:
- If gaps is not empty, is_complete must be false.
- If issues is not empty, is_accurate must be false.
- If is_complete or is_accurate is false, recommendation must be "reject" or "needs_review"."""

    def verify(
        self,
        plan: Plan,
        result: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> Verification:
        """
        Verify if the result matches the execution plan.

        Args:
            plan: The current execution plan (source of truth).
            result: Result from sensemaker.
            context: Additional context including memory/step results.

        Returns:
            Verification result.
        """
        answer = result.get("answer", "")

        # Build evidence from memory entries (actual code executed and results)
        evidence_str = self._format_memory_evidence(context)

        # Format plan steps
        plan_str = plan.format_steps()

        prompt = f"""Please verify the following answer against the execution plan:

Plan Understanding: {plan.query_understanding}

Plan Steps:
{plan_str}

Answer: {answer}

{evidence_str}

VERIFICATION CHECKLIST:
1. Does the answer match what the plan's steps describe?
2. Did any step encounter an error that was never resolved by a later execution?
3. Do the results seem like legitimate answers, or do they indicate abnormalities (e.g. negative values where impossible, NaN, empty)?
4. Does the final answer contain an ACTUAL COMPUTED VALUE (not a guess or hallucination)?

Evaluate this answer and provide a verification report as JSON."""

        messages = [{"role": "user", "content": prompt}]
        return self._call_llm(messages, Verification)

    def explain(
        self,
        plan: Plan,
        result: dict[str, Any],
        verification: Verification,
        context: dict[str, Any] | None,
        question: str,
    ) -> str:
        """
        Answer a user question about the solution using full execution context.

        Args:
            plan: The execution plan.
            result: Result from sensemaker.
            verification: The verification result.
            context: Execution memory / step results.
            question: The user's question.

        Returns:
            Explanation string.
        """
        evidence_str = self._format_memory_evidence(context)
        plan_str = plan.format_steps()
        answer = result.get("answer", "")

        prompt = f"""You are explaining a data-analysis answer to the user.
Use the context below to answer their question clearly and concisely.

Plan Steps:
{plan_str}

Answer: {answer}

{evidence_str}

Verification Summary: {verification.summary}

User question: {question}"""

        messages = [{"role": "user", "content": prompt}]
        return self._call_llm(messages, ExplanationResponse).explanation

    def _format_memory_evidence(self, context: dict[str, Any] | None) -> str:
        """
        Format memory entries as evidence showing executed code and results.

        Args:
            context: Context dict containing memory export.

        Returns:
            Formatted evidence string.
        """
        if not context:
            return "Evidence: No execution context available"

        memory = context.get("memory", {})
        entries = memory.get("entries", [])

        if not entries:
            return "Evidence: No computations were executed"

        lines = ["Evidence (executed computations):"]
        for entry in entries:
            # Skip internal context entries (e.g. dataset schemas) — not relevant for verification
            if entry.get("is_internal_context"):
                continue

            step = entry.get("step", "?")
            code = entry.get("code", "")
            success = entry.get("success", False)

            lines.append(f"\n  Step {step}:")
            lines.append(f"    Code executed: {code}")

            if success and entry.get("result") is not None:
                result_str = truncate_for_llm(str(entry["result"]))
                lines.append(f"    Result: {result_str}")
            elif entry.get("error"):
                lines.append(f"    Error: {entry['error']}")

        return "\n".join(lines)
