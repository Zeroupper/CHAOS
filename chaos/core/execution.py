"""Execution engine for the sensemaking loop."""

from typing import Any

from ..agents import InformationSeekingAgent, SensemakerAgent
from ..data.registry import DataRegistry
from ..types import InfoSeekerResult, Plan, StepState
from ..ui.display import (
    agent_status,
    console,
    display_execution_progress,
    display_memory_table,
    display_step_states,
)
from ..ui.export import RunLog
from ..ui.prompts import approve_correction
from .config import Config
from .logger import get_logger
from .state import ExecutionState


class ExecutionEngine:
    """Handles the sensemaking execution loop."""

    def __init__(
        self,
        config: Config,
        info_seeker: InformationSeekingAgent,
        sensemaker: SensemakerAgent,
        state: ExecutionState,
        data_registry: DataRegistry,
        run_log: RunLog,
    ) -> None:
        self.config = config
        self.info_seeker = info_seeker
        self.sensemaker = sensemaker
        self.state = state
        self.data_registry = data_registry
        self.run_log = run_log

        self._logger = get_logger("Orchestrator")

    def execute_plan(self, query: str, plan: Plan) -> dict[str, Any]:
        """Run sensemaking loop with progress display."""
        new_info: InfoSeekerResult | None = None
        last_step: int | None = None
        step_retries = 0

        while True:

            # Process new info and update step states
            with agent_status("sensemaker", "Analyzing information..."):
                sensemaker_result = self.sensemaker.process(query, plan, new_info)

            # Track step retries (only for needs_info status)
            if sensemaker_result.status == "needs_info":
                current_step = sensemaker_result.current_step
                if current_step != last_step:
                    # New step, reset retry counter
                    step_retries = 0
                    last_step = current_step
                else:
                    # Same step, increment retry counter
                    step_retries += 1
                    if step_retries >= self.config.max_step_attempts:
                        console.print(f"[yellow]Max retries ({self.config.max_step_attempts}) reached for step {current_step}, getting best answer...[/yellow]")
                        display_memory_table(self.state.export())
                        final_answer = self.sensemaker.get_answer()
                        return {
                            "answer": final_answer.answer,
                            "supporting_evidence": final_answer.supporting_evidence,
                        }

            # Show current step states (after they've been updated)
            if self.state.step_states:
                display_step_states(self.state.step_states, plan)

            if sensemaker_result.status == "complete":
                console.print("\n[bold green]* Analysis complete![/bold green]")
                display_memory_table(self.state.export())
                # Log completion
                self.run_log.add_entry("sensemaker", "complete", {
                    "answer": sensemaker_result.answer,
                    "supporting_evidence": sensemaker_result.supporting_evidence,
                })
                self.run_log.final_answer = sensemaker_result.answer
                return {
                    "answer": sensemaker_result.answer,
                    "supporting_evidence": sensemaker_result.supporting_evidence,
                }

            # Handle data quality correction proposal
            if sensemaker_result.status == "needs_correction":
                correction_result = self._handle_correction(
                    query, plan, sensemaker_result
                )
                if correction_result is not None:
                    new_info = correction_result
                    continue
                else:
                    # User skipped correction, continue without new info
                    new_info = None
                    continue

            # Log sensemaker request
            self.run_log.add_entry("sensemaker", "request", {
                "current_step": sensemaker_result.current_step,
                "request": sensemaker_result.request,
                "reasoning": sensemaker_result.reasoning,
            })

            # Show what sensemaker is requesting
            console.print(f"\n[bold]Sensemaker Request:[/bold] {sensemaker_result.request}")
            if sensemaker_result.reasoning:
                console.print(f"[dim]Reasoning: {sensemaker_result.reasoning}[/dim]")

            # Execute information seeking
            new_info = self._seek_with_retries(query, sensemaker_result.request)

            # Log info seeker response
            self.run_log.add_entry("info_seeker", "response", {
                "source": new_info.source,
                "code": new_info.params.get("code", ""),
                "result": new_info.results,
                "success": new_info.success,
            })

            # Display execution result
            display_execution_progress(
                step=sensemaker_result.current_step,
                total=len(plan.steps),
                code=new_info.params.get("code", ""),
                result=new_info.results,
                source=new_info.source,
                success=new_info.success,
            )

    def _seek_with_retries(self, query: str, info_request: str) -> InfoSeekerResult:
        """Seek information with retry logic. Info-seeker handles error recovery via prompt."""
        error_history: list[str] = []
        new_info: InfoSeekerResult | None = None

        for attempt in range(self.config.max_code_retries):
            # Build request with error context for retries
            if error_history:
                error_context = "\n".join(f"- Attempt {i+1}: {e}" for i, e in enumerate(error_history))
                request_with_context = f"{info_request}\n\nPrevious errors:\n{error_context}"
            else:
                request_with_context = info_request

            with agent_status("info_seeker", "Seeking information..."):
                new_info = self.info_seeker.seek(request_with_context)

            if new_info.success:
                return new_info

            error_history.append(new_info.results)
            self._logger.warning(
                f"InfoSeeker attempt {attempt + 1}/{self.config.max_code_retries} failed: {new_info.results}"
            )

        self._logger.error(f"InfoSeeker failed after {self.config.max_code_retries} attempts")

        assert new_info is not None
        return new_info

    def _handle_correction(
        self,
        query: str,
        plan: Plan,
        correction: Any,  # NeedsCorrectionResponse
    ) -> InfoSeekerResult | None:
        """
        Handle a data quality correction proposal from the sensemaker.

        Shows the correction to the user, gets approval/modification,
        and executes the corrected request.

        Args:
            query: Original user query.
            plan: Current execution plan.
            correction: NeedsCorrectionResponse from sensemaker.

        Returns:
            InfoSeekerResult from executing the correction, or None if skipped.
        """
        from ..types import NeedsCorrectionResponse

        if not isinstance(correction, NeedsCorrectionResponse):
            return None

        # Log correction proposal
        self.run_log.add_entry("correction", "proposed", {
            "affected_step": correction.affected_step,
            "issue_description": correction.issue_description,
            "proposed_correction": correction.proposed_correction,
            "reasoning": correction.reasoning,
        })

        # Show correction proposal to user and get decision
        decision, modified_request = approve_correction(
            step=correction.affected_step,
            issue=correction.issue_description,
            proposed_fix=correction.proposed_correction,
        )

        # Log user decision
        self.run_log.add_entry("user", "correction_decision", {
            "decision": decision,
            "modified_request": modified_request,
        })

        if decision == "skip":
            console.print("[yellow]Skipping correction, continuing with original data.[/yellow]")
            # Mark the step as completed with user_accepted so sensemaker moves on
            # and doesn't propose the same correction again
            step_state = self.state.get_step_state(correction.affected_step)
            if step_state:
                self.state.set_step_state(
                    correction.affected_step,
                    StepState(
                        step=correction.affected_step,
                        status="completed",
                        result=step_state.result,
                        user_accepted=True,
                    ),
                )
                # Update current step tracking
                if correction.affected_step >= self.state.current_step:
                    self.state.current_step = correction.affected_step
            return None

        # Determine the request to execute
        if decision == "approve":
            request = correction.proposed_correction
        else:  # modify
            request = modified_request or correction.proposed_correction

        console.print(f"\n[cyan]Executing corrected request for step {correction.affected_step}...[/cyan]")
        console.print(f"[dim]Request: {request}[/dim]\n")

        # Reset the step state so it can be re-executed
        self.sensemaker.reset_step(correction.affected_step)
        # Set current step to the affected step so the result is recorded correctly
        self.state.current_step = correction.affected_step

        # Execute the corrected request
        new_info = self._seek_with_retries(query, request)

        # Log corrected info seeker response
        self.run_log.add_entry("info_seeker", "response", {
            "source": new_info.source,
            "code": new_info.params.get("code", ""),
            "result": new_info.results,
            "success": new_info.success,
            "is_correction": True,
        })

        # Display execution result
        display_execution_progress(
            step=correction.affected_step,
            total=len(plan.steps),
            code=new_info.params.get("code", ""),
            result=new_info.results,
            source=new_info.source,
            success=new_info.success,
        )

        return new_info
