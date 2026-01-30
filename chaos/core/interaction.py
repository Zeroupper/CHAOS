"""Human interaction handling for the orchestrator."""

from typing import TYPE_CHECKING, Any

from ..agents import InformationSeekingAgent, PlannerAgent, SensemakerAgent
from ..data.registry import DataRegistry
from ..memory import Memory
from ..types import Plan, PlanStep
from ..ui.display import console, display_execution_progress, display_plan
from ..ui.export import RunLog
from ..ui.prompts import (
    approve_plan,
    get_new_step_action,
    get_replan_suggestion,
    get_revised_request,
    select_step_to_revise,
)

if TYPE_CHECKING:
    from .context import ContextBuilder
    from .execution import ExecutionEngine


class InteractionHandler:
    """Handles human interaction flows during orchestration."""

    def __init__(
        self,
        execution_engine: "ExecutionEngine",
        info_seeker: InformationSeekingAgent,
        sensemaker: SensemakerAgent,
        planner: PlannerAgent,
        memory: Memory,
        data_registry: DataRegistry,
        context_builder: "ContextBuilder",
        run_log: RunLog,
    ) -> None:
        self.execution = execution_engine
        self.info_seeker = info_seeker
        self.sensemaker = sensemaker
        self.planner = planner
        self.memory = memory
        self.data_registry = data_registry
        self.context = context_builder
        self.run_log = run_log

    def handle_revision(
        self, query: str, plan: Plan, step_history: list[dict]
    ) -> dict[str, Any] | None:
        """Handle user revision of a specific step or adding a new step."""
        selection = select_step_to_revise(step_history)
        if selection is None:
            return None

        # Handle adding a new step
        if selection == "add_new":
            return self.handle_add_new_step(query, plan)

        # Handle revising an existing step
        step_num = selection
        step_info = next((s for s in step_history if s["step"] == step_num), None)
        if not step_info:
            return None

        revised_request = get_revised_request(step_info.get("action", ""))
        if revised_request is None:
            return None

        console.print(f"\n[cyan]Re-executing step {step_num} with your revision...[/cyan]\n")

        new_info = self.info_seeker.seek(revised_request)
        display_execution_progress(
            step=step_num,
            total=len(plan.steps),
            code=new_info.params.get("code", ""),
            result=new_info.results,
            source=new_info.source,
            success=new_info.success,
        )

        return self.execution.execute_plan(query, plan)

    def handle_add_new_step(self, query: str, plan: Plan) -> dict[str, Any] | None:
        """Handle adding a new step to the plan."""
        new_action = get_new_step_action()
        if not new_action or not new_action.strip():
            return None

        # Create new step with next step number
        new_step_num = len(plan.steps) + 1
        new_step = PlanStep(step=new_step_num, action=new_action.strip(), modified=True)
        plan.steps.append(new_step)

        console.print(f"\n[cyan]Added step {new_step_num}: {new_action}[/cyan]")
        console.print("[cyan]Executing new step...[/cyan]\n")

        # Build context with previous step results so info_seeker knows what values exist
        step_context = self.context.build_step_context_for_info_seeker(plan)

        # Execute the new step with context
        new_info = self.info_seeker.seek(new_action, context=step_context)
        display_execution_progress(
            step=new_step_num,
            total=len(plan.steps),
            code=new_info.params.get("code", ""),
            result=new_info.results,
            source=new_info.source,
            success=new_info.success,
        )

        # Store result in memory so sensemaker knows this step was executed
        self.memory.add(
            code=new_info.params.get("code", ""),
            result=new_info.results if new_info.success else None,
            success=new_info.success,
            error=new_info.results if not new_info.success else None,
            step=new_step_num,
        )

        # Mark step as completed in sensemaker's state
        self.sensemaker.mark_step_completed(
            new_step_num,
            new_info.results if new_info.success else None,
            new_info.results if not new_info.success else None,
        )

        # Continue sensemaking with the updated plan
        return self.execution.execute_plan(query, plan)

    def handle_replan(
        self, query: str, step_history: list[dict], modify_plan_func: Any
    ) -> dict[str, Any] | None:
        """
        Handle user request to replan while keeping successful results.

        Uses prompt engineering to pass previous results and suggested fix
        to the regular planner, then restarts the full loop.

        Args:
            query: The original user query.
            step_history: List of step execution results.
            modify_plan_func: Function to modify plan steps.

        Returns:
            Dict with new result and plan, or None if cancelled.
        """
        # Get optional suggested fix from user
        suggested_fix = get_replan_suggestion()
        if suggested_fix is None:
            return None

        console.print("\n[cyan]Creating new plan with learnings from previous attempt...[/cyan]\n")

        # Build replan context from memory and step history
        replan_context = self.context.build_replan_context(step_history, suggested_fix)

        # Get available sources and append replan context
        available_sources = self.data_registry.get_sources_prompt()
        enhanced_sources = f"{available_sources}\n{replan_context}"

        # Use regular create_plan with enhanced context
        new_plan = self.planner.create_plan(query, enhanced_sources)

        # Show the new plan for approval
        while True:
            display_plan(new_plan)
            decision = approve_plan(new_plan)

            if decision == "approve":
                break
            elif decision == "reject":
                console.print("[yellow]Replan rejected.[/yellow]")
                return None
            elif decision == "modify":
                new_plan = modify_plan_func(new_plan)
            elif decision is None:
                console.print("[yellow]Operation cancelled.[/yellow]")
                return None

        # Clear memory for fresh start (learnings are in the plan context)
        self.memory.clear()
        self.sensemaker.reset()

        # Execute the new plan
        console.print("\n[bold]Executing revised plan...[/bold]\n")
        new_result = self.execution.execute_plan(query, new_plan)

        return {"result": new_result, "plan": new_plan}
