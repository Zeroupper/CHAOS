"""Sensemaking loop for plan execution."""

from typing import Any

from ..agents import InformationSeekingAgent, SensemakerAgent
from ..types import InfoSeekerResult, Plan, ReviewResponse, StepState
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


class SensemakingLoop:
    """Handles the sensemaking execution loop."""

    def __init__(
        self,
        config: Config,
        info_seeker: InformationSeekingAgent,
        sensemaker: SensemakerAgent,
        state: ExecutionState,
    ) -> None:
        self.config = config
        self.info_seeker = info_seeker
        self.sensemaker = sensemaker
        self.state = state

        self._logger = get_logger("Orchestrator")

    def _finalize_result(
        self, result: dict[str, Any], run_log: RunLog, reason: str = "complete"
    ) -> dict[str, Any]:
        """Log completion, display memory table, and return result."""
        run_log.add_entry("sensemaker", reason, result)
        run_log.final_answer = result.get("answer")
        display_memory_table(self.state.export())
        return result

    def _seek_and_display(
        self, request: str, step: int, plan: Plan, run_log: RunLog, is_review: bool = False
    ) -> InfoSeekerResult:
        """Execute info seeker request and display results."""
        with agent_status("info_seeker", "Seeking information..."):
            result = self.info_seeker.seek(request)
        self._log_info_seeker_response(run_log, result, is_review)
        display_execution_progress(
            step=step,
            total=len(plan.steps),
            code=result.params.get("code", ""),
            result=result.results,
            source=result.source,
            success=result.success,
        )
        return result

    def execute_plan(self, query: str, plan: Plan, run_log: RunLog) -> dict[str, Any]:
        """Run sensemaking loop with progress display."""
        if not plan.steps:
            console.print("\n[yellow]No steps to execute.[/yellow]")
            return {"answer": "No data analysis needed for this query.", "supporting_evidence": []}

        new_info: InfoSeekerResult | None = None
        step_attempts: dict[int, int] = {}

        while True:
            with agent_status("sensemaker", "Analyzing information..."):
                sensemaker_result = self.sensemaker.process(query, plan, new_info)

            # Track step attempts and check for max attempts (execute only)
            if sensemaker_result.status == "execute":
                current_step = sensemaker_result.current_step
                step_attempts[current_step] = step_attempts.get(current_step, 0) + 1
                if step_attempts[current_step] > self.config.max_step_attempts:
                    console.print(f"[yellow]Max attempts ({self.config.max_step_attempts}) reached for step {current_step}, getting best answer...[/yellow]")
                    return self._finalize_result(
                        self.sensemaker.get_answer().model_dump(exclude={"status"}), run_log, "max_attempts"
                    )

            if self.state.step_states:
                display_step_states(self.state.step_states, plan)

            match sensemaker_result.status:
                case "complete":
                    console.print("\n[bold green]* Analysis complete![/bold green]")
                    return self._finalize_result(
                        sensemaker_result.model_dump(exclude={"status"}), run_log
                    )

                case "review":
                    new_info = self._handle_review(plan, sensemaker_result, run_log)
                    continue

                case _:  # execute
                    run_log.add_entry("sensemaker", "request", sensemaker_result.model_dump(exclude={"status"}))
                    console.print(f"\n[bold]Sensemaker Request:[/bold] {sensemaker_result.request}")
                    if sensemaker_result.reasoning:
                        console.print(f"[dim]Reasoning: {sensemaker_result.reasoning}[/dim]")

                    new_info = self._seek_and_display(
                        sensemaker_result.request, sensemaker_result.current_step, plan, run_log
                    )

    def _log_info_seeker_response(
        self, run_log: RunLog, info: InfoSeekerResult, is_review: bool = False
    ) -> None:
        """Log an info seeker response to the run log."""
        data = info.model_dump()
        if is_review:
            data["is_review"] = True
        run_log.add_entry("info_seeker", "response", data)

    def _handle_review(
        self,
        plan: Plan,
        review: ReviewResponse,
        run_log: RunLog,
    ) -> InfoSeekerResult | None:
        """
        Handle a data quality review proposal from the sensemaker.

        Shows the review to the user, gets approval/modification,
        and executes the corrected request.

        Args:
            plan: Current execution plan.
            review: ReviewResponse from sensemaker.
            run_log: Run log for recording events.

        Returns:
            InfoSeekerResult from executing the correction, or None if skipped.
        """
        if not isinstance(review, ReviewResponse):
            return None

        # Log review proposal
        run_log.add_entry("review", "proposed", review.model_dump(exclude={"status"}))

        # Show review proposal to user and get decision
        decision, modified_request = approve_correction(
            step=review.affected_step,
            issue=review.issue_description,
            proposed_fix=review.proposed_correction,
        )

        # Log user decision
        run_log.add_entry("user", "review_decision", {
            "decision": decision,
            "modified_request": modified_request,
        })

        if decision == "skip":
            console.print("[yellow]Skipping correction, continuing with original data.[/yellow]")
            # Mark the step as completed with user_accepted so sensemaker moves on
            # and doesn't propose the same correction again
            step_state = self.state.get_step_state(review.affected_step)
            if step_state:
                self.state.set_step_state(
                    review.affected_step,
                    StepState(
                        step=review.affected_step,
                        status="completed",
                        result=step_state.result,
                        user_accepted=True,
                    ),
                )
                # Update current step tracking
                if review.affected_step >= self.state.current_step:
                    self.state.current_step = review.affected_step
            return None

        # Determine the request to execute
        if decision == "approve":
            request = review.proposed_correction
        else:  # modify
            request = modified_request or review.proposed_correction

        console.print(f"\n[cyan]Executing corrected request for step {review.affected_step}...[/cyan]")
        console.print(f"[dim]Request: {request}[/dim]\n")

        # Reset the step state so it can be re-executed
        self.sensemaker.reset_step(review.affected_step)
        # Set current step to the affected step so the result is recorded correctly
        self.state.current_step = review.affected_step

        # Execute the corrected request
        new_info = self._seek_and_display(
            request, review.affected_step, plan, run_log, is_review=True
        )

        return new_info
