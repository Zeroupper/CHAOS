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
    NeedsCorrectionResponse,
    NeedsInfoResponse,
    Plan,
    RecoveryGuidance,
    SensemakerResponse,
    StepState,
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
    - Detect and diagnose data quality issues
    """

    def __init__(
        self, config: Config, llm_client: StructuredLLMClient, memory: Memory
    ) -> None:
        super().__init__(config, llm_client)
        self.memory = memory
        self._current_step = 0  # Track which plan step we're on
        self._step_states: dict[int, StepState] = {}  # Track state per step
        self._system_prompt = """You are a sensemaking agent. Your task is to execute a plan step-by-step and synthesize the results.

You will be given step states that track the progress of each step:
- "pending": Step has not been executed yet
- "completed": Step executed successfully with valid result
- "needs_clarification": Step returned suspicious result, clarification was requested
- "failed": Clarification confirmed data is missing/unavailable

Based on the step states and results, respond with JSON in one of these formats:

If ALL steps in the plan are "completed" (no "pending" steps remain):
{
    "status": "complete",
    "answer": "The computed answer from the step results",
    "supporting_evidence": ["Values from each completed step"]
}

If you need to execute a step or request clarification:
{
    "status": "needs_info",
    "current_step": <step number>,
    "request": "What to execute or clarify",
    "reasoning": "Why this is needed"
}

If clarification reveals a DATA QUALITY ISSUE that can be fixed (e.g., placeholder values like -1, missing data markers, etc.):
{
    "status": "needs_correction",
    "affected_step": <step number with the issue>,
    "issue_description": "Clear description of the data quality problem",
    "proposed_correction": "A corrected query/request that avoids the issue",
    "reasoning": "Why this correction will fix the issue"
}

If any step is "failed" and CANNOT be corrected (data truly missing/unavailable):
{
    "status": "complete",
    "answer": "Cannot complete: [explanation]. Successfully computed: [what worked].",
    "supporting_evidence": ["Evidence of what succeeded and what failed"]
}

RULES:
1. NEVER do math yourself - all computations via Python. Even simple subtraction/addition must be executed via Python.
2. Execute steps IN ORDER - don't skip ahead
3. For computations, include actual values from previous steps in your request (e.g., "Compute 155.0 - (-1.0)")
4. When a step shows "needs_clarification", wait for clarification result before proceeding
5. When clarification reveals FIXABLE data quality issues (placeholders, sentinel values like -1, etc.), use "needs_correction" to propose a fix
6. Only mark as "failed" when data is truly missing and cannot be fixed
7. USER MODIFIED steps must be followed EXACTLY as written
8. NEVER propose corrections for steps marked "(USER ACCEPTED - do not propose corrections)" - the user has explicitly chosen to use the original value
9. NEVER return "complete" if ANY step is still "pending" - you MUST execute all steps in order first"""

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
        # Store new information in memory and update step states
        if new_info:
            self.memory.add(
                code=new_info.params.get("code", ""),
                result=new_info.results if new_info.success else None,
                success=new_info.success,
                error=new_info.results if not new_info.success else None,
                step=self._current_step,
            )

            # Update step state based on result
            if new_info.success:
                self._update_step_state(self._current_step, new_info.results)

        # Build context for LLM
        memory_context = self.memory.get_context_for_llm()
        plan_steps = self._format_plan_steps(plan)
        step_states_str = self._format_step_states(plan)

        # Format new info if available
        new_info_str = ""
        if new_info:
            info_dict = {
                "request": new_info.request,
                "source": new_info.source,
                "success": new_info.success,
                "results": new_info.results,
            }
            new_info_str = f"\nLatest result:\n{json.dumps(info_dict, indent=2, default=str)}"

        prompt = f"""Query: {query}

Plan Steps:
{plan_steps}

Step States:
{step_states_str}

{memory_context}
{new_info_str}

Based on the step states, decide what to do next."""

        messages = [{"role": "user", "content": prompt}]
        result = self._call_llm(
            messages, Union[CompleteResponse, NeedsInfoResponse, NeedsCorrectionResponse]
        )

        # Update current step tracking for needs_info responses
        if result.status == "needs_info":
            if result.current_step != self._current_step:
                self._current_step = result.current_step
            else:
                self._current_step += 1

        return result

    def _update_step_state(self, step: int, result: str) -> None:
        """Update step state based on result."""
        current_state = self._step_states.get(step)
        is_suspicious = self._is_suspicious_result(result)

        if current_state and current_state.status == "needs_clarification":
            # This is a clarification response
            if is_suspicious or self._confirms_missing_data(result):
                self._step_states[step] = StepState.from_result(
                    step, "failed", current_state.result, current_state,
                    clarification_response=result,
                    failure_reason=f"Clarification confirmed: {result}",
                )
            else:
                self._step_states[step] = StepState.from_result(
                    step, "completed", result, current_state,
                    clarification_response=result,
                )
        elif is_suspicious:
            self._step_states[step] = StepState.from_result(step, "needs_clarification", result)
        else:
            self._step_states[step] = StepState.from_result(step, "completed", result)

    def _is_suspicious_result(self, result: str) -> bool:
        """Check if result appears suspicious (NaN, null, empty)."""
        if not result:
            return True

        result_lower = result.strip().lower()

        # Check if entire result is a null-like value
        if result_lower in ["nan", "null", "none", "n/a", ""]:
            return True

        # Check if result contains NaN values in JSON
        # Common patterns: "NaN", ": NaN", ": null"
        suspicious_patterns = [": nan", ":nan", '"nan"', ": null", ":null", '"null"', ": none", '"none"']
        for pattern in suspicious_patterns:
            if pattern in result_lower:
                return True

        return False

    def _confirms_missing_data(self, result: str) -> bool:
        """Check if clarification result confirms missing data."""
        # A result of "0" or empty for count queries indicates no data
        result_stripped = result.strip()
        if result_stripped == "0":
            return True
        if result_stripped.lower() in ["[]", "{}", "empty", "no data"]:
            return True
        return False

    def _format_plan_steps(self, plan: Plan) -> str:
        """Format plan steps for the prompt."""
        # Use Plan.format_steps() but customize modified step text
        if not plan.steps:
            return "No specific steps in plan."

        lines = []
        for step in plan.steps:
            source_str = f" (from {step.source})" if step.source else ""
            if step.modified:
                lines.append(
                    f"  Step {step.step} [USER MODIFIED - FOLLOW EXACTLY]: "
                    f"{step.action}{source_str}"
                )
            else:
                lines.append(f"  Step {step.step}: {step.action}{source_str}")
        return "\n".join(lines)

    def _format_step_states(self, plan: Plan) -> str:
        """Format step states for the prompt."""
        if not plan.steps:
            return "No steps defined."

        lines = []
        for plan_step in plan.steps:
            step_num = plan_step.step
            state = self._step_states.get(step_num)

            if not state:
                lines.append(f"  Step {step_num}: [pending] - Not yet executed")
            elif state.status == "completed":
                result_str = state.result or ""
                if len(result_str) > 100:
                    result_str = result_str[:100] + "..."
                # Include acknowledgment note if user accepted a suspicious value
                if state.clarification_response and "acknowledged" in state.clarification_response.lower():
                    lines.append(f"  Step {step_num}: [completed] result={result_str} (USER ACCEPTED - do not propose corrections)")
                else:
                    lines.append(f"  Step {step_num}: [completed] result={result_str}")
            elif state.status == "needs_clarification":
                lines.append(
                    f"  Step {step_num}: [needs_clarification] "
                    f"suspicious_result={state.result} - ASK FOR VERIFICATION"
                )
            elif state.status == "failed":
                lines.append(
                    f"  Step {step_num}: [failed] "
                    f"reason={state.failure_reason}"
                )

        return "\n".join(lines)

    def reset(self) -> None:
        """Reset step tracking for a new query."""
        self._current_step = 0
        self._step_states = {}

    def reset_step(self, step: int) -> None:
        """Reset a specific step to pending state (used after correction)."""
        if step in self._step_states:
            del self._step_states[step]
        # Reset current step to re-execute from this step
        if step <= self._current_step:
            self._current_step = step - 1

    def mark_step_completed(
        self, step: int, result: str | None, error: str | None = None
    ) -> None:
        """
        Manually mark a step as completed (used for user-added steps).

        Args:
            step: Step number to mark.
            result: The result if successful.
            error: The error if failed.
        """
        if error:
            self._step_states[step] = StepState(
                step=step,
                status="failed",
                error=error,
                failure_reason=error,
            )
        else:
            self._step_states[step] = StepState(
                step=step,
                status="completed",
                result=result,
            )
        # Update current step to be at or past this step
        if step >= self._current_step:
            self._current_step = step

    @property
    def step_results(self) -> dict[int, str]:
        """Get step results for backward compatibility."""
        return {
            step: state.result
            for step, state in self._step_states.items()
            if state.result is not None
        }

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
        return self._call_llm(messages, RecoveryGuidance)
