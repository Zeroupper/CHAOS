"""Main orchestrator that coordinates the multi-agent pipeline with human-in-the-loop."""

from typing import Any

from ..agents import (
    InformationSeekingAgent,
    PlannerAgent,
    SensemakerAgent,
    VerifierAgent,
)
from ..agents.explorer import ExplorerAgent
from ..data.registry import DataRegistry
from ..llm.structured_client import StructuredLLMClient
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
    display_verification,
)
from ..ui.export import RunLog, export_verbose_transcript, offer_export_to_user
from ..ui.prompts import approve_plan, final_review, get_explain_question, get_plan_feedback
from .code_executor import CodeExecutor
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
    ) -> None:
        self.config = config
        self.llm_client = llm_client
        self.data_registry = data_registry or DataRegistry()
        self.state = ExecutionState()
        self.run_log: RunLog | None = None

        # Centralized code executor
        self._executor = CodeExecutor(config, self.data_registry)

        # Initialize agents
        self.explorer = ExplorerAgent(self.data_registry)
        self.planner = PlannerAgent(config, llm_client)
        self.sensemaker = SensemakerAgent(config, llm_client, self.state)
        self.info_seeker = InformationSeekingAgent(
            config, llm_client, self.data_registry, self._executor, self.state
        )
        self.verifier = VerifierAgent(config, llm_client)

        # Initialize helpers
        self._sensemaking_loop = SensemakingLoop(
            config=config,
            info_seeker=self.info_seeker,
            sensemaker=self.sensemaker,
            state=self.state,
            executor=self._executor,
        )
        self._interaction = InteractionHandler(
            config=config,
            sensemaking_loop=self._sensemaking_loop,
            info_seeker=self.info_seeker,
            sensemaker=self.sensemaker,
            planner=self.planner,
            state=self.state,
            data_registry=self.data_registry,
            executor=self._executor,
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
        self._executor.reset()

        # Initialize run log for export (also stored on self for eval access)
        run_log = RunLog(query=query)
        self.run_log = run_log

        console.print(f"\n[bold cyan]Processing:[/bold cyan] {query}\n")
        if self.config.sandbox:
            console.print("[dim]Sandbox mode enabled — code will run in Docker container[/dim]\n")

        # Step 1a: Explore data — inspect all dataset schemas
        available_sources = self.data_registry.get_sources_prompt()
        schemas = self.explorer.explore()
        data_context = "DATASET SCHEMAS (use these exact column names):\n" + "\n".join(
            str(s) for s in schemas
        )
        run_log.data_context = data_context

        # Step 1b: Create plan from exploration results
        with agent_status("planner", "Creating execution plan..."):
            plan = self.planner.create_plan(query, available_sources, data_context)

        # Human reviews plan (or auto-approve)
        display_plan(plan)
        if self.config.auto_approve:
            console.print("[dim]Auto-approved plan.[/dim]")
        else:
            while True:
                decision = approve_plan(plan)

                if decision == "approve":
                    break
                elif decision == "reject":
                    console.print("[yellow]Plan rejected.[/yellow]")
                    return REJECTED_RESULT
                elif decision == "modify":
                    plan = self._modify_plan(plan)
                    display_plan(plan)
                elif decision is None:
                    console.print("[yellow]Operation cancelled.[/yellow]")
                    return CANCELLED_RESULT

        run_log.set_plan(plan)

        # Step 2: Execute sensemaking loop
        console.print("\n[bold]Starting execution...[/bold]\n")
        result = self._sensemaking_loop.execute_plan(query, plan, run_log)

        # Step 3: Verification and human review
        verification: Verification | None = None
        while True:
            if verification is None:
                verification_context = {
                    "memory": self.state.export(),
                }
                with agent_status("verifier", "Verifying answer..."):
                    verification = self.verifier.verify(plan, result, verification_context)
                display_verification(verification, result.get("answer", ""))

            step_history = build_step_history(self.state.get_entries(), plan)

            if self.config.auto_approve:
                final_decision = "accept"
                console.print("[dim]Auto-approved final answer.[/dim]")
            else:
                final_decision = final_review(verification.recommendation, bool(step_history))

            if final_decision == "accept":
                final_result = self._finalize(result, verification, plan)
                offer_export_to_user(run_log, result, verification, export_dir, self.config.auto_approve)
                self._maybe_export_verbose(run_log)
                return final_result
            elif final_decision == "reject":
                console.print("[yellow]Answer rejected.[/yellow]")
                offer_export_to_user(run_log, result, verification, export_dir, self.config.auto_approve)
                self._maybe_export_verbose(run_log)
                return REJECTED_RESULT
            elif final_decision == "revise":
                revised = self._interaction.handle_revision(query, plan, step_history, run_log)
                if revised:
                    result = revised
                    verification = None
            elif final_decision == "explain":
                from rich.panel import Panel

                while True:
                    question = get_explain_question()
                    if not question:
                        break
                    with agent_status("verifier", "Explaining..."):
                        explanation = self.verifier.explain(
                            plan, result, verification, verification_context, question
                        )
                    console.print(Panel(explanation, title="Explanation", border_style="cyan"))
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

    def _maybe_export_verbose(self, run_log: RunLog) -> None:
        """Export verbose LLM transcript if enabled and a normal export was saved."""
        if not self.config.verbose_export:
            return
        if not run_log.export_path:
            return
        verbose_path = run_log.export_path.replace(".md", "_verbose.md")
        try:
            out = export_verbose_transcript(self.llm_client.transcript, verbose_path)
            console.print(f"[green]Verbose transcript exported to:[/green] {out}")
        except Exception as e:
            console.print(f"[red]Failed to export verbose transcript:[/red] {e}")

    def _modify_plan(self, plan: Plan) -> Plan:
        """Allow user to modify plan via feedback to the planner."""
        feedback = get_plan_feedback()
        if not feedback:
            return plan
        with agent_status("planner", "Revising plan..."):
            return self.planner.modify_plan(plan, feedback)

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
