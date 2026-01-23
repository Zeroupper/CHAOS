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

Be critical but fair. A good answer should directly answer the query with supporting evidence."""

    def execute(
        self,
        query: str,
        result: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> Verification:
        """Verify the result."""
        return self.verify(query, result, context)

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

        # Build context section with plan
        context_str = ""
        if context:
            plan = context.get("plan")
            if plan is not None:
                context_str += "\nPlan Steps:\n"
                if isinstance(plan, Plan):
                    for step in plan.steps:
                        context_str += f"  Step {step.step}: {step.action}\n"
                elif isinstance(plan, dict) and plan.get("steps"):
                    for step in plan["steps"]:
                        step_num = step.get("step", "?")
                        action = step.get("action", "Unknown")
                        context_str += f"  Step {step_num}: {action}\n"

        prompt = f"""Please verify the following answer to a query:

Original Query: {query}

Answer: {answer}

{evidence_str}
{context_str}

VERIFICATION CHECKLIST:
1. Does the answer contain an ACTUAL COMPUTED VALUE (not a guess)?
2. Do the step results show the computation was actually performed?
3. Does the final answer match the computed results from the steps?
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
            content = entry.get("content", {})
            if isinstance(content, dict) and "code" in content:
                step = content.get("step", "?")
                source = content.get("source", "unknown")
                code = content.get("code", "")
                success = content.get("success", False)

                lines.append(f"\n  Step {step} on '{source}':")
                lines.append(f"    Code executed: {code}")

                if success and "result" in content:
                    result_str = str(content["result"])
                    if len(result_str) > 500:
                        result_str = result_str[:500] + "..."
                    lines.append(f"    Result: {result_str}")
                elif "error" in content:
                    lines.append(f"    Error: {content['error']}")

        return "\n".join(lines)

    def generate_report(self, verification: Verification) -> str:
        """Generate human-readable report."""
        gaps = verification.gaps
        issues = verification.issues

        return f"""
=== Verification Report ===
Completeness: {'Yes' if verification.is_complete else 'No'}
Accuracy: {'Yes' if verification.is_accurate else 'No'}
Confidence: {verification.confidence_score:.2f}

Gaps: {', '.join(gaps) if gaps else 'None identified'}
Issues: {', '.join(issues) if issues else 'None identified'}

Summary: {verification.summary or 'No summary provided'}
Recommendation: {verification.recommendation.upper()}
"""
