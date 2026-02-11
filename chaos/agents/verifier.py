"""Verifier agent - validates answers against the execution plan."""

from typing import Any

from ..core.config import Config
from ..llm.structured_client import StructuredLLMClient
from ..types import Plan, Verification
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
        self._system_prompt = """You are a verification agent. Your task is to evaluate answers against the execution plan.

The execution plan is the sole source of truth. It defines what should be computed.
Verify that the answer correctly reflects the computation described in the plan steps.

When verifying an answer, check:
1. Does the answer match what the plan's steps describe?
2. Were all plan steps executed successfully?
3. Is the answer supported by the provided evidence?
4. Are there any gaps, inconsistencies, or issues?

Respond with a JSON object:
{
    "is_complete": true/false,
    "is_accurate": true/false,
    "confidence_score": 0.0 to 1.0,
    "gaps": ["List of any missing information or gaps"],
    "issues": ["List of any problems or concerns"],
    "summary": "Brief summary of the verification",
    "recommendation": "approve" | "reject" | "needs_review"
}

CRITICAL CONSISTENCY RULES:
- If "gaps" is NOT empty, then "is_complete" MUST be false
- If "issues" is NOT empty, then "is_accurate" MUST be false
- If "is_complete" is false OR "is_accurate" is false, then "recommendation" MUST be "reject" or "needs_review"
- "confidence_score" should reflect the severity of gaps/issues (more gaps/issues = lower score)

Be critical but fair. A good answer should match the plan's intended computation with supporting evidence."""

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
2. Were all plan steps executed and do the results support the answer?
3. Does the final answer contain an ACTUAL COMPUTED VALUE (not a guess)?
4. Are there any signs of hallucinated or guessed values?

Evaluate this answer and provide a verification report as JSON."""

        messages = [{"role": "user", "content": prompt}]
        return self._call_llm(messages, Verification)

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
            step = entry.get("step", "?")

            if entry.get("is_internal_context"):
                lines.append(f"\n  Step {step} (context):")
                lines.append(f"    {entry.get('result', '')}")
                continue

            code = entry.get("code", "")
            success = entry.get("success", False)

            lines.append(f"\n  Step {step}:")
            lines.append(f"    Code executed: {code}")

            if success and entry.get("result") is not None:
                result_str = str(entry["result"])
                if len(result_str) > 500:
                    result_str = result_str[:500] + "..."
                lines.append(f"    Result: {result_str}")
            elif entry.get("error"):
                lines.append(f"    Error: {entry['error']}")

        return "\n".join(lines)
