"""Verifier agent - validates answers and creates reports."""

from typing import Any

from ..core.config import Config
from ..llm.structured_client import StructuredLLMClient
from ..types import Plan, Verification
from .base import BaseAgent


class VerifierAgent(BaseAgent):
    """
    Verifies whether the sensemaker's answer addresses the user query.

    Responsibilities:
    - Evaluate answer completeness
    - Check answer accuracy
    - Identify gaps or issues
    - Generate human-readable report
    """

    def __init__(self, config: Config, llm_client: StructuredLLMClient) -> None:
        super().__init__(config, llm_client)
        self._system_prompt = """You are a verification agent. Your task is to evaluate answers and ensure they properly address the original query.

When verifying an answer, check:
1. Does the answer directly address the query?
2. Is the answer complete and comprehensive?
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

Be critical but fair. A good answer should directly answer the query with supporting evidence."""

    def verify(
        self,
        query: str,
        result: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> Verification:
        """
        Verify if the result answers the query.

        Args:
            query: Original user query.
            result: Result from sensemaker.
            context: Additional context including plan and step results.

        Returns:
            Verification result.
        """
        answer = result.get("answer", "")

        # Build evidence from memory entries (actual code executed and results)
        evidence_str = self._format_memory_evidence(context)

        # Build context section with plan (noting modified steps)
        context_str = ""
        has_modified_steps = False
        if context:
            plan = context.get("plan")
            if isinstance(plan, Plan):
                context_str += "\nPlan Steps:\n" + plan.format_steps() + "\n"
                has_modified_steps = any(s.modified for s in plan.steps)

        # Add note about modified steps taking precedence
        modified_note = ""
        if has_modified_steps:
            modified_note = """
CRITICAL: Some plan steps were ADDED or MODIFIED BY THE USER. When verifying:
- Steps marked [USER MODIFIED] represent CORRECTIONS the user made to fix issues
- User-added steps are AUTHORITATIVE - they override previous results
- The FINAL user-modified step's result should be used as the answer
- Previous steps may have produced incorrect results that the user corrected
- Verify the answer against the LATEST user-modified step result
- If the user added a step to correct a calculation, THAT step's result is correct
"""

        prompt = f"""Please verify the following answer to a query:

Original Query: {query}

Answer: {answer}

{evidence_str}
{context_str}
{modified_note}
VERIFICATION CHECKLIST:
1. Does the answer contain an ACTUAL COMPUTED VALUE (not a guess)?
2. Do the step results show the computation was actually performed?
3. Does the final answer match the computed results from the steps?
4. Are there any signs of hallucinated or guessed values?
5. If there are USER MODIFIED steps:
   - These are CORRECTIONS added by the user to fix previous errors
   - The result from the LAST user-modified step should be the answer
   - User-modified steps OVERRIDE earlier step results
   - If user added step N to correct step M's result, use step N's result

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

        # Get modified step numbers from plan
        modified_steps: set[int] = set()
        plan = context.get("plan")
        if isinstance(plan, Plan):
            modified_steps = {s.step for s in plan.steps if s.modified}

        lines = ["Evidence (executed computations):"]
        for entry in entries:
            step = entry.get("step", "?")
            code = entry.get("code", "")
            success = entry.get("success", False)

            # Mark user-modified steps prominently
            if step in modified_steps:
                lines.append(f"\n  Step {step} [USER ADDED/MODIFIED - AUTHORITATIVE]:")
            else:
                lines.append(f"\n  Step {step}:")
            lines.append(f"    Code executed: {code}")

            if success and entry.get("result") is not None:
                result_str = str(entry["result"])
                if len(result_str) > 500:
                    result_str = result_str[:500] + "..."
                if step in modified_steps:
                    lines.append(f"    Result: {result_str} ← USE THIS (user correction)")
                else:
                    lines.append(f"    Result: {result_str}")
            elif entry.get("error"):
                lines.append(f"    Error: {entry['error']}")

        return "\n".join(lines)
