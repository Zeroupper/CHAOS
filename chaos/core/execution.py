"""Execution engine for the sensemaking loop."""

from typing import Any

from ..agents import InformationSeekingAgent, SensemakerAgent
from ..data.registry import DataRegistry
from ..memory import Memory
from ..types import InfoSeekerResult, Plan, StepState
from ..ui.display import (
    console,
    display_execution_progress,
    display_memory_table,
    display_step_states,
)
from ..ui.export import RunLog
from ..ui.prompts import approve_correction
from .config import Config
from .logger import get_logger


class ExecutionEngine:
    """Handles the sensemaking execution loop."""

    def __init__(
        self,
        config: Config,
        info_seeker: InformationSeekingAgent,
        sensemaker: SensemakerAgent,
        memory: Memory,
        data_registry: DataRegistry,
        run_log: RunLog,
    ) -> None:
        self.config = config
        self.info_seeker = info_seeker
        self.sensemaker = sensemaker
        self.memory = memory
        self.data_registry = data_registry
        self.run_log = run_log

        self._orch_logger = get_logger("Orchestrator")
        self._sensemaker_logger = get_logger("Sensemaker")

    def execute_plan(self, query: str, plan: Plan) -> dict[str, Any]:
        """Run sensemaking loop with progress display."""
        iteration = 0
        new_info: InfoSeekerResult | None = None

        while iteration < self.config.max_iterations:
            iteration += 1
            console.print(f"\n[bold cyan]=== Iteration {iteration}/{self.config.max_iterations} ===[/bold cyan]")

            # Process new info and update step states
            sensemaker_result = self.sensemaker.process(query, plan, new_info)

            # Show current step states (after they've been updated)
            if self.sensemaker._step_states:
                display_step_states(self.sensemaker._step_states, plan)

            if sensemaker_result.status == "complete":
                console.print("\n[bold green]* Analysis complete![/bold green]")
                display_memory_table(self.memory.export())
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

        # Max iterations reached
        console.print("[yellow]Max iterations reached, getting best answer...[/yellow]")
        display_memory_table(self.memory.export())
        final_answer = self.sensemaker.get_answer()
        return {
            "answer": final_answer.answer,
            "supporting_evidence": final_answer.supporting_evidence,
        }

    def _seek_with_retries(self, query: str, info_request: str) -> InfoSeekerResult:
        """Seek information with retry logic and sensemaker guidance on failure."""
        error_history: list[dict[str, Any]] = []
        current_request = info_request
        new_info: InfoSeekerResult | None = None

        for attempt in range(self.config.max_retries):
            new_info = self.info_seeker.seek(current_request)

            if new_info.success:
                return new_info

            error_entry = {
                "attempt": attempt + 1,
                "request": current_request,
                "error": new_info.results,
            }
            error_history.append(error_entry)

            self._orch_logger.warning(
                f"InfoSeeker attempt {attempt + 1}/{self.config.max_retries} failed: {error_entry['error']}"
            )

            # Get guidance from sensemaker for retry
            if attempt < self.config.max_retries - 1:
                self._sensemaker_logger.debug("Consulting sensemaker for recovery guidance...")
                available_sources = self.data_registry.get_sources_prompt()
                recovery = self.sensemaker.guide_recovery(
                    query=query,
                    original_request=info_request,
                    error_history=error_history,
                    available_sources=available_sources,
                )
                self._sensemaker_logger.info(f"Recovery summary: {recovery.summary}")
                self._sensemaker_logger.info(f"Revised request: {recovery.revised_request}")
                current_request = recovery.revised_request or current_request

        self._orch_logger.error(f"InfoSeeker failed after {self.config.max_retries} attempts")

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
            # Mark the step as completed with acknowledgment so sensemaker moves on
            # and doesn't propose the same correction again
            step_state = self.sensemaker._step_states.get(correction.affected_step)
            if step_state:
                self.sensemaker._step_states[correction.affected_step] = StepState(
                    step=correction.affected_step,
                    status="completed",
                    result=step_state.result,
                    clarification_response="User acknowledged suspicious value and chose to continue with original data",
                )
                # Update current step tracking
                if correction.affected_step >= self.sensemaker._current_step:
                    self.sensemaker._current_step = correction.affected_step
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
