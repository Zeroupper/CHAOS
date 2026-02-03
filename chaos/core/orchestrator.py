"""Main orchestrator that coordinates the multi-agent pipeline with human-in-the-loop."""

from typing import Any

from ..agents import (
    InformationSeekingAgent,
    PlannerAgent,
    SensemakerAgent,
    VerifierAgent,
)
from ..data.registry import DataRegistry
from ..llm.structured_client import StructuredLLMClient
from ..tools.base import BaseTool
from ..types import (
    CANCELLED_RESULT,
    REJECTED_RESULT,
    Plan,
    Verification,
)
from ..ui.display import (
    agent_status,
    console,
    display_plan,
    display_tool_execution,
    display_verification,
)
from ..ui.export import RunLog, offer_export_to_user
from ..ui.prompts import approve_plan, final_review, modify_plan_step
from .config import Config
from .context import build_step_history
from .execution import SensemakingLoop
from .interaction import InteractionHandler
from .state import ExecutionState


class Orchestrator:
    """
    Orchestrates the multi-agent sensemaking pipeline with human-in-the-loop.

    Flow:
    1. Planner creates execution plan from user query
    2. Human reviews/modifies plan
    3. Sensemaker + InformationSeeker loop until COMPLETE
    4. Verifier validates the answer
    5. Human reviews final answer
    """

    def __init__(
        self,
        config: Config,
        llm_client: StructuredLLMClient,
        data_registry: DataRegistry | None = None,
        planner_tools: list[BaseTool] | None = None,
    ) -> None:
        self.config = config
        self.llm_client = llm_client
        self.data_registry = data_registry or DataRegistry()
        self.state = ExecutionState()

        # Initialize agents
        self.planner = PlannerAgent(
            config, llm_client, tools=planner_tools, on_tool_execute=display_tool_execution
        )
        self.sensemaker = SensemakerAgent(config, llm_client, self.state)
        self.info_seeker = InformationSeekingAgent(config, llm_client, self.data_registry)
        self.verifier = VerifierAgent(config, llm_client)

        # Initialize helpers
        self._sensemaking_loop = SensemakingLoop(
            config=config,
            info_seeker=self.info_seeker,
            sensemaker=self.sensemaker,
            state=self.state,
        )
        self._interaction = InteractionHandler(
            sensemaking_loop=self._sensemaking_loop,
            info_seeker=self.info_seeker,
            sensemaker=self.sensemaker,
            planner=self.planner,
            state=self.state,
            data_registry=self.data_registry,
        )

    def run(self, query: str, export_dir: str | None = None) -> dict[str, Any]:
        """
        Execute pipeline with human interaction.

        Args:
            query: User query to process.
            export_dir: Optional directory for run exports. If provided, user will
                        be prompted to export at the end.

        Returns:
            Result dictionary with answer, verification, etc.
        """
        self.state.reset()

        # Initialize run log for export
        run_log = RunLog(query=query)

        console.print(f"\n[bold cyan]Processing:[/bold cyan] {query}\n")

        # Step 1: Create and review plan
        available_sources = self.data_registry.get_sources_prompt()
        with agent_status("planner", "Creating execution plan..."):
            plan = self.planner.create_plan(query, available_sources)

        # Human reviews plan
        while True:
            display_plan(plan)
            decision = approve_plan(plan)

            if decision == "approve":
                break
            elif decision == "reject":
                console.print("[yellow]Plan rejected.[/yellow]")
                return REJECTED_RESULT
            elif decision == "modify":
                plan = self._modify_plan(plan)
            elif decision is None:
                console.print("[yellow]Operation cancelled.[/yellow]")
                return CANCELLED_RESULT

        # Log the approved plan
        run_log.set_plan(plan)

        # Step 2: Execute sensemaking loop
        console.print("\n[bold]Starting execution...[/bold]\n")
        result = self._sensemaking_loop.execute_plan(query, plan, run_log)

        # Step 3: Verification and human review
        verification: Verification | None = None
        while True:
            if verification is None:
                verification_context = {
                    "plan": plan,
                    "memory": self.state.export(),
                }
                with agent_status("verifier", "Verifying answer..."):
                    verification = self.verifier.verify(query, result, verification_context)
                display_verification(verification, result.get("answer", ""))

            step_history = build_step_history(self.state.get_entries(), plan)
            final_decision = final_review(verification.recommendation, bool(step_history))

            if final_decision == "accept":
                final_result = self._finalize(result, verification, plan)
                offer_export_to_user(run_log, result, verification, export_dir)
                return final_result
            elif final_decision == "reject":
                console.print("[yellow]Answer rejected.[/yellow]")
                offer_export_to_user(run_log, result, verification, export_dir)
                return REJECTED_RESULT
            elif final_decision == "revise":
                revised = self._interaction.handle_revision(query, plan, step_history, run_log)
                if revised:
                    result = revised
                    verification = None
            elif final_decision == "replan":
                replan_result = self._interaction.handle_replan(
                    query, step_history, self._modify_plan, run_log
                )
                if replan_result:
                    result = replan_result["result"]
                    plan = replan_result["plan"]
                    # Update run log with new plan
                    run_log.set_plan(plan)
                    verification = None
            elif final_decision is None:
                console.print("[yellow]Operation cancelled.[/yellow]")
                return CANCELLED_RESULT

    def _modify_plan(self, plan: Plan) -> Plan:
        """Allow user to modify plan steps."""
        for step in plan.steps:
            new_action = modify_plan_step(step.step, step.action)
            if new_action and new_action != step.action:
                step.action = new_action
                step.modified = True
        return plan

    def _finalize(
        self,
        result: dict[str, Any],
        verification: Verification,
        plan: Plan | None = None,
    ) -> dict[str, Any]:
        """Prepare final output."""
        return {
            "answer": result.get("answer"),
            "confidence": verification.confidence_score,
            "supporting_evidence": result.get("supporting_evidence", []),
            "verification": verification.model_dump(),
            "plan": plan.model_dump() if plan else None,
        }
