"""Sensemaker agent - updates memory and synthesizes information."""

import json
from typing import Any, Union

from ..core.config import Config
from ..llm.structured_client import StructuredLLMClient
from ..memory import Memory
from ..types import (
    CompleteResponse,
    FinalAnswer,
    InfoSeekerResult,
    NeedsInfoResponse,
    Plan,
    RecoveryGuidance,
    SensemakerResponse,
)
from .base import BaseAgent


class SensemakerAgent(BaseAgent):
    """
    Updates its memory based on information from the InformationSeekingAgent.

    Responsibilities:
    - Process incoming information
    - Update working memory
    - Track plan step progress
    - Synthesize understanding
    - Decide when task is COMPLETE
    """

    def __init__(
        self, config: Config, llm_client: StructuredLLMClient, memory: Memory
    ) -> None:
        super().__init__(config, llm_client)
        self.memory = memory
        self._current_step = 0  # Track which plan step we're on
        self._step_results: dict[int, Any] = {}  # Store results per step
        self._system_prompt = """You are a sensemaking agent. Your task is to execute a plan step-by-step and synthesize the results.

IMPORTANT: You must follow the plan steps IN ORDER. Do not skip steps or mark complete until ALL steps have been executed with actual computed results.

Given a query, plan, current step, and gathered information, you must:
1. Check which step of the plan you are currently on
2. If the current step has results, verify they are actual computed values (not raw data lists)
3. If results are valid, move to the next step
4. Only mark "complete" when ALL plan steps are done AND the FINAL step result is in memory

Always respond with a JSON object in one of these formats:

If ALL plan steps are complete and the FINAL computed result is in memory:
{
    "status": "complete",
    "answer": "Your answer - MUST be a value that exists in the step results",
    "supporting_evidence": ["The actual computed values from each step"]
}

If you need to execute the next step:
{
    "status": "needs_info",
    "current_step": 1,
    "request": "Execute step N: [exact step description from plan]. Use the data source X and compute Y.",
    "reasoning": "Why this step is needed according to the plan"
}

CRITICAL RULES - READ CAREFULLY:

1. NEVER PERFORM MATH YOURSELF - ALL computations must be executed via Python code:
   - Addition, subtraction, multiplication, division
   - Rounding, averaging, percentages
   - ANY mathematical operation whatsoever

2. If a plan step involves computation (e.g., "Calculate X + Y", "Round to 2 decimals"):
   - You MUST request that step to be executed via Python
   - Do NOT calculate it yourself and mark complete

3. You can ONLY mark "complete" when:
   - ALL plan steps have corresponding results in memory
   - The FINAL answer is a value that was computed by Python (visible in step results)
   - You are NOT doing any calculation to produce the answer

4. Your answer in "complete" status must be EXACTLY a value from the step results.
   - WRONG: Computing (78.5 + 155) / 2 = 116.75 yourself
   - RIGHT: Requesting Python to compute it, then reporting the result

5. REUSE PREVIOUS RESULTS - When requesting a computation step that uses values from previous steps:
   - Include the ACTUAL VALUES from previous steps in your request
   - The information seeker should use these values directly, not recalculate them
   - Format: "Calculate using: average=78.50438924168846, maximum=155.0. Compute (average/2 + maximum/2) rounded to 2 decimals"

Example - if plan has 3 steps and step 3 is "Calculate (avg/2 + max/2) rounded to 2 decimals":
- After step 2: You have avg=78.50438924168846, max=155.0 in memory
- Request step 3: "Execute step 3: Using average=78.50438924168846 and maximum=155.0 from previous steps, calculate (average/2 + maximum/2) rounded to 2 decimals"
- After step 3: Memory shows result=116.75 → NOW you can mark complete with answer=116.75"""

    def execute(
        self,
        query: str,
        plan: Plan,
        new_info: InfoSeekerResult | None = None,
    ) -> SensemakerResponse:
        """
        Process information and update understanding.

        Args:
            query: Original user query.
            plan: Execution plan from planner.
            new_info: New information from information seeker.

        Returns:
            SensemakerResponse (CompleteResponse or NeedsInfoResponse).
        """
        return self.process(query, plan, new_info)

    def process(
        self,
        query: str,
        plan: Plan,
        new_info: InfoSeekerResult | None = None,
    ) -> SensemakerResponse:
        """Process new information and update memory."""
        # Store new information in memory and track step results
        if new_info:
            # Use typed conversion to memory entry
            memory_entry = new_info.to_memory_entry(self._current_step)
            self.memory.update({"content": memory_entry.model_dump()})

            # Store result for current step (only on success)
            if new_info.success:
                self._step_results[self._current_step] = new_info.results

        # Build context for LLM
        memory_context = self.memory.get_context_for_llm()
        plan_steps = self._format_plan_steps(plan)
        total_steps = len(plan.steps)

        # Format step progress
        step_progress = self._format_step_progress(total_steps)

        # Format new info if available
        new_info_str = ""
        if new_info:
            info_dict = {
                "request": new_info.request,
                "source": new_info.source,
                "success": new_info.success,
                "results": new_info.results,
            }
            new_info_str = f"\nResult from previous request:\n{json.dumps(info_dict, indent=2, default=str)}"

        prompt = f"""Query: {query}

Plan Steps:
{plan_steps}

{step_progress}

{memory_context}
{new_info_str}

Based on the plan and results so far:
1. Have ALL plan steps been executed with actual computed results?
2. If not, what is the NEXT step that needs to be executed?
3. If you have raw data but need a computation (like average), request that computation explicitly.

Respond with JSON indicating either 'complete' with the ACTUAL COMPUTED answer, or 'needs_info' with the specific next step to execute."""

        messages = [{"role": "user", "content": prompt}]
        # Use discriminated union - Instructor handles this via the 'status' field
        result = self._call_llm(messages, Union[CompleteResponse, NeedsInfoResponse])

        # Update current step tracking for needs_info responses
        if result.status == "needs_info":
            if result.current_step != self._current_step:
                self._current_step = result.current_step
            else:
                self._current_step += 1

        return result

    def _format_plan_steps(self, plan: Plan) -> str:
        """Format plan steps for the prompt."""
        if not plan.steps:
            return "No specific steps in plan."

        lines = []
        for step in plan.steps:
            source_str = f" (from {step.source})" if step.source else ""
            lines.append(f"  Step {step.step}: {step.action}{source_str}")
        return "\n".join(lines)

    def _format_step_progress(self, total_steps: int) -> str:
        """Format current step progress."""
        if not self._step_results:
            return f"Progress: No steps completed yet. Current step: 1/{total_steps}"

        lines = [f"Progress: {len(self._step_results)}/{total_steps} steps completed."]
        lines.append("Completed step results:")
        for step_num, result in self._step_results.items():
            # Truncate long results for display
            result_str = str(result)
            if len(result_str) > 200:
                result_str = result_str[:200] + "..."
            lines.append(f"  Step {step_num}: {result_str}")
        lines.append(f"Next step to execute: {len(self._step_results) + 1}")
        return "\n".join(lines)

    def reset(self) -> None:
        """Reset step tracking for a new query."""
        self._current_step = 0
        self._step_results = {}

    def _summarize_plan(self, plan: Plan) -> str:
        """Create a brief summary of the plan."""
        lines = []
        if plan.query_understanding:
            lines.append(f"Understanding: {plan.query_understanding}")
        if plan.required_info:
            lines.append(f"Required info: {', '.join(plan.required_info[:5])}")
        if plan.data_sources:
            lines.append(f"Data sources: {', '.join(plan.data_sources)}")
        return "\n".join(lines) if lines else "No plan details available"

    def get_answer(self) -> FinalAnswer:
        """Generate final answer from accumulated knowledge."""
        prompt = f"""Based on all the information gathered:

{self.memory.get_context_for_llm()}

Provide a final comprehensive answer.
Respond with JSON containing 'answer' and 'supporting_evidence'."""

        messages = [{"role": "user", "content": prompt}]
        return self._call_llm(messages, FinalAnswer)

    def guide_recovery(
        self,
        query: str,
        original_request: str,
        error_history: list[dict[str, Any]],
        available_sources: str,
    ) -> RecoveryGuidance:
        """
        Provide guidance for the information seeker after execution errors.

        Args:
            query: Original user query.
            original_request: The information request that failed.
            error_history: List of error attempts with error messages.
            available_sources: Description of available data sources.

        Returns:
            RecoveryGuidance with guidance for the next attempt.
        """
        errors_str = "\n".join(
            f"Attempt {i+1}: {e.get('error', 'Unknown error')}"
            for i, e in enumerate(error_history)
        )

        prompt = f"""The information seeker failed to execute a query. Help guide it to a better approach.

Original user query: {query}

Information request that failed: {original_request}

Error history:
{errors_str}

{available_sources}

Analyze what went wrong and suggest a different approach. Consider:
- Are the column names correct?
- Is the data source appropriate for this query?
- Should the query be simplified or broken into parts?
- Are there alternative ways to get the same information?

Respond with JSON:
{{
    "summary": "Brief summary of what went wrong",
    "analysis": "Why the errors occurred",
    "revised_request": "A new, corrected information request",
    "guidance": "Specific guidance for the new approach"
}}"""

        messages = [{"role": "user", "content": prompt}]
        recovery = self._call_llm(messages, RecoveryGuidance)

        # Store recovery attempt in memory
        self.memory.update({
            "content": {
                "type": "error_recovery",
                "original_request": original_request,
                "errors": errors_str,
                "summary": recovery.summary,
                "revised_approach": recovery.revised_request,
            }
        })

        return recovery
