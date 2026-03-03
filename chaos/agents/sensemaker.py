"""Sensemaker agent - updates memory and synthesizes information."""

import json
from typing import Union

from ..core.config import Config
from ..core.logger import truncate_for_llm
from ..core.state import ExecutionState
from ..llm.structured_client import StructuredLLMClient
from ..types import (
    CompleteResponse,
    ExecuteResponse,
    InfoSeekerResult,
    Plan,
    ReviewResponse,
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
        self._system_prompt = """Execute a plan step-by-step. Respond with ONE of these JSON formats:

Execute next step:
{"status": "execute", "current_step": <int>, "request": "<str: what to compute>", "reasoning": "<str>"}

All steps done:
{"status": "complete", "answer": "<str: final value>", "supporting_evidence": ["<str>"]}

Data quality issue:
{"status": "review", "affected_step": <int>, "issue_description": "<str>", "proposed_correction": "<str>", "reasoning": "<str>"}

RULES:
- Never compute math yourself — always use "execute".
- Steps run in order: after step N, next is N+1.
- Reference previous results as `step_N_result`.
- If a step fails with a code error, re-execute with fixed instructions (do NOT use "review").
- If a step returns NaN/null after one retry, accept it and complete.
- Follow USER MODIFIED steps exactly. Never re-correct USER ACCEPTED values."""

    def process(
        self,
        query: str,
        plan: Plan,
        new_info: InfoSeekerResult | None = None,
        data_context: str = "",
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
        plan_steps = plan.format_steps()
        step_states_str = self.state.format_step_states(plan)

        # Format new info if available
        new_info_str = ""
        if new_info:
            # Truncate results for LLM context (full values are passed via step_N_result)
            results_preview = truncate_for_llm(new_info.results)
            info_dict = {
                "request": new_info.request,
                "source": new_info.source,
                "success": new_info.success,
                "results": results_preview,
            }
            new_info_str = f"\nLatest result:\n{json.dumps(info_dict, indent=2, default=str)}"

        # Include dataset schemas only when reviewing data quality issues
        # (failed steps or NaN results that may need column name correction)
        schema_block = ""
        if data_context and self._has_failed_or_nan_steps():
            schema_block = f"\n{data_context}\nUse these exact column names when proposing corrections.\n"

        prompt = f"""Query: {query}

Plan Steps:
{plan_steps}

Step States:
{step_states_str}

{memory_context}
{new_info_str}
{schema_block}
Based on the step states, decide what to do next."""

        messages = [{"role": "user", "content": prompt}]
        result = self._call_llm(
            messages, Union[CompleteResponse, ExecuteResponse, ReviewResponse]
        )

        # Update current step tracking for execute responses
        if result.status == "execute":
            self.state.current_step = result.current_step

        return result
                
    def _has_failed_or_nan_steps(self) -> bool:
        """Check if any step has failed or returned a NaN/null-like result."""
        for step_state in self.state.step_states.values():
            if step_state.status == "failed":
                return True
            if step_state.result and any(
                marker in str(step_state.result).lower()
                for marker in ("nan", "null", "none")
            ):
                return True
        return False

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

    def get_answer(self) -> CompleteResponse:
        """Generate final answer from accumulated knowledge."""
        prompt = f"""Based on all the information gathered:

{self.state.get_context_for_llm()}

Provide a final concise answer...
Respond with JSON containing 'status' (always "complete"), 'answer' and 'supporting_evidence'."""

        messages = [{"role": "user", "content": prompt}]
        return self._call_llm(messages, CompleteResponse)
