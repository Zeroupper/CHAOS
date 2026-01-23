"""Interactive orchestrator with human-in-the-loop."""

from typing import Any

from ..types import InfoSeekerResult, Plan
from ..ui.display import (
    console,
    display_execution_progress,
    display_plan,
    display_verification,
)
from ..ui.prompts import (
    approve_plan,
    final_review,
    get_revised_request,
    modify_plan_step,
    select_step_to_revise,
)
from .orchestrator import Orchestrator


class InteractiveOrchestrator(Orchestrator):
    """Orchestrator with human interaction at plan review and final verification."""

    def run(self, query: str) -> dict[str, Any]:
        """Execute pipeline with human interaction."""
        self.memory.clear()
        self.sensemaker.reset()

        console.print(f"\n[bold cyan]Processing:[/bold cyan] {query}\n")

        # Step 1: Create and review plan
        available_sources = self.data_registry.get_sources_prompt()
        plan = self.planner.create_plan(query, available_sources)

        # HUMAN INTERACTION: Plan review loop
        while True:
            display_plan(plan)
            decision = approve_plan(plan)

            if decision == "approve":
                break
            elif decision == "reject":
                console.print("[yellow]Plan rejected.[/yellow]")
                return {"answer": None, "status": "rejected"}
            elif decision == "modify":
                plan = self._modify_plan_interactive(plan)
                # Loop back to show modified plan
            elif decision is None:
                # User cancelled (Ctrl+C)
                console.print("[yellow]Operation cancelled.[/yellow]")
                return {"answer": None, "status": "cancelled"}

        # Step 2: Automatic sensemaking execution (with progress display)
        console.print("\n[bold]Starting execution...[/bold]\n")
        result = self._run_sensemaking_with_display(query, plan)

        # Step 3: Verification and human review loop
        while True:
            verification_context = {
                "plan": plan,
                "step_results": self.sensemaker._step_results,
                "memory": self.memory.export(),
            }
            verification = self.verifier.verify(query, result, verification_context)

            # HUMAN INTERACTION: Final review
            display_verification(verification, result.get("answer", ""))

            # Build step history for revision selection
            step_history = self._build_step_history()
            final_decision = final_review(
                verification.recommendation, bool(step_history)
            )

            if final_decision == "accept":
                return self._finalize(result, verification, plan)
            elif final_decision == "reject":
                console.print("[yellow]Answer rejected.[/yellow]")
                return {"answer": None, "status": "rejected"}
            elif final_decision == "revise":
                # Let user select and fix a step
                revised = self._handle_revision(query, plan, step_history)
                if revised:
                    result = revised
                    # Loop back to verification with new result
            elif final_decision is None:
                # User cancelled (Ctrl+C)
                console.print("[yellow]Operation cancelled.[/yellow]")
                return {"answer": None, "status": "cancelled"}

    def _modify_plan_interactive(self, plan: Plan) -> Plan:
        """Allow user to modify plan steps."""
        for step in plan.steps:
            new_action = modify_plan_step(step.step, step.action)
            if new_action and new_action != step.action:
                step.action = new_action
                step.modified = True  # Mark step as modified by user
        return plan

    def _run_sensemaking_with_display(
        self, query: str, plan: Plan
    ) -> dict[str, Any]:
        """Run sensemaking loop with progress display (no human approval per step)."""
        iteration = 0
        new_info: InfoSeekerResult | None = None
        result: dict[str, Any] = {"answer": "", "supporting_evidence": []}

        while iteration < self.config.max_iterations:
            iteration += 1
            console.print(
                f"[dim]======= Iteration {iteration}/{self.config.max_iterations} =======[/dim]"
            )

            sensemaker_result = self.sensemaker.process(query, plan, new_info)

            if sensemaker_result.status == "complete":
                console.print("[green]Analysis complete![/green]\n")
                return {
                    "answer": sensemaker_result.answer,
                    "supporting_evidence": sensemaker_result.supporting_evidence,
                }

            # Execute information seeking and display progress
            info_request = sensemaker_result.request
            new_info = self._seek_with_retries(query, info_request)

            # Display what was executed
            display_execution_progress(
                step=sensemaker_result.current_step,
                total=len(plan.steps),
                code=new_info.params.get("code", ""),
                result=new_info.results,
                source=new_info.source,
                success=new_info.success,
            )

        # Max iterations reached
        console.print(
            "[yellow]Max iterations reached, getting best answer...[/yellow]"
        )
        final_answer = self.sensemaker.get_answer()
        return {
            "answer": final_answer.answer,
            "supporting_evidence": final_answer.supporting_evidence,
        }

    def _build_step_history(self) -> list[dict]:
        """Build list of executed steps with their results for revision selection."""
        history = []
        memory = self.memory.export()
        for entry in memory.get("entries", []):
            content = entry.get("content", {})
            if isinstance(content, dict) and "step" in content:
                history.append(
                    {
                        "step": content.get("step"),
                        "source": content.get("source"),
                        "action": content.get("code", ""),
                        "result": content.get("result") or content.get("error", ""),
                        "success": content.get("success", False),
                    }
                )
        return history

    def _handle_revision(
        self, query: str, plan: Plan, step_history: list[dict]
    ) -> dict[str, Any] | None:
        """Handle user revision of a specific step."""
        step_num = select_step_to_revise(step_history)
        if step_num is None:
            return None

        # Find the original step
        original_step = next(
            (s for s in step_history if s["step"] == step_num), None
        )
        if not original_step:
            return None

        # Get revised request from user
        revised_request = get_revised_request(original_step.get("action", ""))
        if revised_request is None:
            return None

        console.print(
            f"\n[cyan]Re-executing step {step_num} with your revision...[/cyan]\n"
        )

        # Execute the revised request
        new_info = self.info_seeker.seek(revised_request)

        display_execution_progress(
            step=step_num,
            total=len(plan.steps),
            code=new_info.params.get("code", ""),
            result=new_info.results,
            source=new_info.source,
            success=new_info.success,
        )

        # Continue sensemaking from here
        return self._run_sensemaking_with_display(query, plan)
