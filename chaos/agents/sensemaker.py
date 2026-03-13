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
        self._system_prompt = """Execute a plan step-by-step. Respond with ONE of the provided JSON response types.

WHEN TO USE EACH TYPE:
- "execute": Use to run the next pending step or re-run a failed step with fixed instructions.
- "complete": All steps are done and results are available. Provide the final answer.
- "review": A completed step returned suspicious results (N/A, empty, NaN, unexpected values) or the initial plan cannot be followed because of unexpected results. Proposes a correction to the plan step — NOT a code fix.

RULES:
- Never compute math yourself — always use "execute".
- Steps run in order: after step N, next is N+1.
- Reference previous results as `step_N_result`.
- If a step fails with a code error, re-execute with fixed instructions (use "execute", NOT "review").
- Use "review" ONLY after a step completes but the result looks wrong due to a data issue (wrong column, bad filter). Never use "review" before a step has been attempted.
- If a step returns NaN/null after one retry, accept it and complete.
- Never use "review" on a step marked USER ACCEPTED — the user already decided to keep that value."""

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

    def get_final_answer(self, query: str, raw_answer: str = "") -> CompleteResponse:
        """Extract a clean final answer from step results.

        If no step completed successfully, returns N/A without calling the LLM.
        Otherwise makes a lightweight LLM call to extract just the result value.
        """
        has_completed = any(
            s.status == "completed" and s.result is not None
            for s in self.state.step_states.values()
        )
        if not has_completed:
            return CompleteResponse(
                answer="N/A",
                supporting_evidence=["No step completed successfully."],
            )

        prompt = f"""Based on the step results, provide the final answer.

RULES:
- "answer" must directly answer the query. State the result value first, optionally followed by one short sentence of context (e.g. "0.611 (Pearson correlation from 89 paired observations).").
- Use the value from the last computed step as the definitive result. Do NOT recompute or second-guess code correctness.
- Only answer "N/A" if a crucial step failed or returned a null/NaN value.
- "supporting_evidence" should list the key step results that support the answer.

Query: {query}

Step results:
{self.state.get_context_for_llm()}"""

        if raw_answer:
            prompt += f"\n\nRaw answer: {raw_answer}"

        messages = [{"role": "user", "content": prompt}]
        return self._call_llm(messages, CompleteResponse)
