"""Sensemaker agent - updates memory and synthesizes information."""

import json
from typing import Union

from ..core.config import Config
from ..core.state import ExecutionState
from ..llm.structured_client import StructuredLLMClient
from ..types import (
    CompleteResponse,
    InfoSeekerResult,
    NeedsCorrectionResponse,
    NeedsInfoResponse,
    Plan,
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
        self, config: Config, llm_client: StructuredLLMClient, state: ExecutionState
    ) -> None:
        super().__init__(config, llm_client)
        self.state = state
        self._system_prompt = """You are a sensemaking agent. Your task is to execute a plan step-by-step and synthesize the results.

You will be given step states that track the progress of each step:
- "pending": Step has not been executed yet
- "completed": Step executed successfully with valid result
- "failed": Step failed and cannot proceed

Based on the step states and results, respond with JSON in one of these formats:

If ALL steps in the plan are "completed" (no "pending" steps remain):
{
    "status": "complete",
    "answer": "The computed answer from the step results",
    "supporting_evidence": ["Values from each completed step"]
}

If you need to execute a step:
{
    "status": "needs_info",
    "current_step": <step number>,
    "request": "What to execute",
    "reasoning": "Why this is needed"
}

If a result appears to have a DATA QUALITY ISSUE that can be fixed:
{
    "status": "needs_correction",
    "affected_step": <step number with the issue>,
    "issue_description": "Clear description of the data quality problem",
    "proposed_correction": "A corrected query/request that avoids the issue",
    "reasoning": "Why this correction will fix the issue"
}

If any step has truly missing/unavailable data that CANNOT be corrected:
{
    "status": "complete",
    "answer": "Cannot complete: [explanation]. Successfully computed: [what worked].",
    "supporting_evidence": ["Evidence of what succeeded and what failed"]
}

RESULT QUALITY EVALUATION:
When you receive a result, evaluate whether it appears valid in context:
- NaN, null, None, -1 as standalone values may indicate missing data
- Empty results [], {} may indicate no matching data
- Use judgment: -1 for temperature is suspicious, -1 for a delta might be valid
If you suspect issues, use "needs_correction" to propose a fix.

RULES:
1. NEVER do math yourself - all computations via Python. Even simple subtraction/addition must be executed via Python.
2. Execute steps IN ORDER - don't skip ahead
3. For computations, include actual values from previous steps in your request (e.g., "Compute 155.0 - (-1.0)")
4. USER MODIFIED steps must be followed EXACTLY as written
5. NEVER propose corrections for steps marked "(USER ACCEPTED - do not propose corrections)" - the user has explicitly chosen to use the original value
6. NEVER return "complete" if ANY step is still "pending" - you MUST execute all steps in order first"""

    def process(
        self,
        query: str,
        plan: Plan,
        new_info: InfoSeekerResult | None = None,
    ) -> SensemakerResponse:
        """Process new information and update memory."""
        # Store new information in state
        if new_info:
            self.state.record_result(
                step=self.state.current_step,
                code=new_info.params.get("code", ""),
                result=new_info.results if new_info.success else None,
                success=new_info.success,
                error=new_info.results if not new_info.success else None,
            )

        # Build context for LLM
        memory_context = self.state.get_context_for_llm()
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
            if result.current_step != self.state.current_step:
                self.state.current_step = result.current_step
            else:
                self.state.current_step += 1

        return result

    def _format_plan_steps(self, plan: Plan) -> str:
        """Format plan steps for the prompt."""
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
            state = self.state.get_step_state(step_num)

            if not state:
                lines.append(f"  Step {step_num}: [pending] - Not yet executed")
            elif state.status == "completed":
                result_str = state.result or ""
                if len(result_str) > 100:
                    result_str = result_str[:100] + "..."
                # Include acknowledgment note if user accepted a suspicious value
                if state.user_accepted:
                    lines.append(f"  Step {step_num}: [completed] result={result_str} (USER ACCEPTED - do not propose corrections)")
                else:
                    lines.append(f"  Step {step_num}: [completed] result={result_str}")
            elif state.status == "failed":
                lines.append(
                    f"  Step {step_num}: [failed] "
                    f"reason={state.failure_reason}"
                )

        return "\n".join(lines)

    def reset(self) -> None:
        """Reset state for a new query."""
        self.state.reset()

    def reset_step(self, step: int) -> None:
        """Reset a specific step to pending state (used after correction)."""
        self.state.reset_step(step)

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
            self.state.set_step_state(
                step,
                StepState(
                    step=step,
                    status="failed",
                    error=error,
                    failure_reason=error,
                ),
            )
        else:
            self.state.set_step_state(
                step,
                StepState(
                    step=step,
                    status="completed",
                    result=result,
                ),
            )
        # Update current step to be at or past this step
        if step >= self.state.current_step:
            self.state.current_step = step

    @property
    def step_results(self) -> dict[int, str]:
        """Get step results for backward compatibility."""
        return self.state.step_results

    def get_answer(self) -> CompleteResponse:
        """Generate final answer from accumulated knowledge."""
        prompt = f"""Based on all the information gathered:

{self.state.get_context_for_llm()}

Provide a final comprehensive answer.
Respond with JSON containing 'status' (always "complete"), 'answer' and 'supporting_evidence'."""

        messages = [{"role": "user", "content": prompt}]
        return self._call_llm(messages, CompleteResponse)
