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
from .code_executor import CodeExecutor
from .config import Config
from .state import ExecutionState


class SensemakingLoop:
    """Handles the sensemaking execution loop."""

    def __init__(
        self,
        config: Config,
        info_seeker: InformationSeekingAgent,
        sensemaker: SensemakerAgent,
        state: ExecutionState,
        executor: CodeExecutor | None = None,
    ) -> None:
        self.config = config
        self.info_seeker = info_seeker
        self.sensemaker = sensemaker
        self.state = state
        self._executor = executor

    def _finalize(
        self, query: str, plan: Plan, run_log: RunLog,
        reason: str = "complete", raw_answer: str = "",
    ) -> dict[str, Any]:
        """Extract final answer, log completion, display memory, return result."""
        self._record_error_summary(plan, reason)
        with agent_status("sensemaker", "Extracting final answer..."):
            clean = self.sensemaker.get_final_answer(query, raw_answer)
        result = clean.model_dump(exclude={"status"})
        run_log.add_entry("sensemaker", reason, result)
        run_log.final_answer = result.get("answer")
        display_memory_table(self.state.export())
        return result

    def _record_error_summary(self, plan: Plan, reason: str) -> None:
        """Record an internal context entry summarizing execution errors, if any."""
        failed_steps: list[int] = []
        pending_steps: list[int] = []

        for plan_step in plan.steps:
            step_num = plan_step.step
            step_state = self.state.get_step_state(step_num)
            if step_state is None:
                pending_steps.append(step_num)
            elif step_state.status == "failed":
                failed_steps.append(step_num)

        parts: list[str] = []
        if reason == "max_attempts":
            parts.append("[EXECUTION ERROR] Max retry attempts reached — plan could not be fully executed.")
        if failed_steps:
            parts.append(f"Steps {failed_steps} failed during execution.")
        if pending_steps:
            parts.append(f"Steps {pending_steps} were never executed.")

        if parts:
            self.state.record_context(step=0, message=" ".join(parts))

    def _seek_and_display(
        self, request: str, step: int, plan: Plan, run_log: RunLog, is_review: bool = False
    ) -> InfoSeekerResult:
        """Execute info seeker request and display results."""
        status_msg = (
            "Running code in sandbox..."
            if self.config.sandbox
            else "Seeking information..."
        )
        with agent_status("info_seeker", status_msg):
            result = self.info_seeker.seek(request)
        data = result.model_dump()
        if is_review:
            data["is_review"] = True
        run_log.add_entry("info_seeker", "response", data)
        display_execution_progress(
            step=step,
            total=len(plan.steps),
            code=result.params.get("code", ""),
            result=result.results,
            source=result.source,
            success=result.success,
            sandbox=self.config.sandbox,
        )
        return result

    def execute_plan(self, query: str, plan: Plan, run_log: RunLog) -> dict[str, Any]:
        """Run sensemaking loop with progress display."""
        if not plan.steps:
            console.print("\n[yellow]No steps to execute.[/yellow]")
            return {"answer": "No data analysis needed for this query.", "supporting_evidence": []}

        if plan.data_context:
            self.state.record_context(step=0, message=plan.data_context)

        new_info: InfoSeekerResult | None = None
        step_attempts: dict[int, int] = {}

        while True:
            with agent_status("sensemaker", "Analyzing information..."):
                response = self.sensemaker.process(
                    query, plan, new_info, data_context=plan.data_context
                )

            if self.state.step_states:
                display_step_states(self.state.step_states, plan)

            match response.status:
                case "complete":
                    console.print("\n[bold green]* Analysis complete![/bold green]")
                    return self._finalize(query, plan, run_log, raw_answer=response.answer)

                case "review":
                    new_info = self._handle_review(plan, response, run_log)

                case _:  # execute
                    step = response.current_step
                    step_attempts[step] = step_attempts.get(step, 0) + 1

                    if step_attempts[step] > self.config.max_step_attempts:
                        console.print(f"[yellow]Max attempts ({self.config.max_step_attempts}) reached for step {step}, getting best answer...[/yellow]")
                        return self._finalize(query, plan, run_log, reason="max_attempts")

                    run_log.add_entry("sensemaker", "request", response.model_dump(exclude={"status"}))
                    console.print(f"\n[bold]Sensemaker Request:[/bold] {response.request}")
                    if response.reasoning:
                        console.print(f"[dim]Reasoning: {response.reasoning}[/dim]")

                    new_info = self._seek_and_display(
                        response.request, step, plan, run_log
                    )

                    if not new_info.success:
                        console.print(
                            f"\n[bold yellow]Step {step} failed — "
                            f"retrying (attempt {step_attempts[step]}"
                            f"/{self.config.max_step_attempts})...[/bold yellow]"
                        )

    def _handle_review(
        self,
        plan: Plan,
        review: ReviewResponse,
        run_log: RunLog,
    ) -> InfoSeekerResult | None:
        """Handle a data quality review proposal from the sensemaker."""
        run_log.add_entry("review", "proposed", review.model_dump(exclude={"status"}))

        if self.config.auto_approve:
            decision, modified_request = "approve", None
        else:
            decision, modified_request = approve_correction(
                step=review.affected_step,
                issue=review.issue_description,
                proposed_fix=review.proposed_correction,
            )

        run_log.add_entry("user", "review_decision", {
            "decision": decision,
            "modified_request": modified_request,
        })

        if decision == "skip":
            console.print("[yellow]Skipping correction, continuing with original data.[/yellow]")
            self.state.record_context(
                review.affected_step,
                f"[DATA CORRECTION] Step {review.affected_step}: {review.issue_description}\nUser skipped correction.",
            )
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
                if review.affected_step >= self.state.current_step:
                    self.state.current_step = review.affected_step
            return None

        request = modified_request or review.proposed_correction if decision == "modify" else review.proposed_correction

        self.state.record_context(
            review.affected_step,
            f"[DATA CORRECTION] Step {review.affected_step}: {review.issue_description}\nUser approved: {request}",
        )

        console.print(f"\n[cyan]Executing corrected request for step {review.affected_step}...[/cyan]")
        console.print(f"[dim]Request: {request}[/dim]\n")

        self.sensemaker.reset_step(review.affected_step)
        if self._executor:
            self._executor.reset_step(review.affected_step)
        self.state.current_step = review.affected_step

        return self._seek_and_display(
            request, review.affected_step, plan, run_log, is_review=True
        )
