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
from ..memory import Memory
from ..tools.base import BaseTool
from ..types import InfoSeekerResult, Plan, PlanStep, Verification
from ..ui.display import (
    console,
    display_execution_progress,
    display_memory_table,
    display_plan,
    display_step_states,
    display_verification,
)
from ..ui.prompts import (
    approve_plan,
    final_review,
    get_new_step_action,
    get_replan_suggestion,
    get_revised_request,
    modify_plan_step,
    select_step_to_revise,
)
from .config import Config
from .logger import get_logger


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
        self.memory = Memory()

        # Initialize loggers
        self._orch_logger = get_logger("Orchestrator")
        self._sensemaker_logger = get_logger("Sensemaker")

        # Initialize agents
        self.planner = PlannerAgent(config, llm_client, tools=planner_tools)
        self.sensemaker = SensemakerAgent(config, llm_client, self.memory)
        self.info_seeker = InformationSeekingAgent(config, llm_client, self.data_registry)
        self.verifier = VerifierAgent(config, llm_client)

    def run(self, query: str) -> dict[str, Any]:
        """Execute pipeline with human interaction."""
        self.memory.clear()
        self.sensemaker.reset()

        console.print(f"\n[bold cyan]Processing:[/bold cyan] {query}\n")

        # Step 1: Create and review plan
        available_sources = self.data_registry.get_sources_prompt()
        plan = self.planner.create_plan(query, available_sources)

        # Human reviews plan
        while True:
            display_plan(plan)
            decision = approve_plan(plan)

            if decision == "approve":
                break
            elif decision == "reject":
                console.print("[yellow]Plan rejected.[/yellow]")
                return {"answer": None, "status": "rejected"}
            elif decision == "modify":
                plan = self._modify_plan(plan)
            elif decision is None:
                console.print("[yellow]Operation cancelled.[/yellow]")
                return {"answer": None, "status": "cancelled"}

        # Step 2: Execute sensemaking loop
        console.print("\n[bold]Starting execution...[/bold]\n")
        result = self._sensemaking_loop(query, plan)

        # Step 3: Verification and human review
        verification = None
        while True:
            if verification is None:
                verification_context = {
                    "plan": plan,
                    "step_results": self.sensemaker.step_results,
                    "memory": self.memory.export(),
                }
                verification = self.verifier.verify(query, result, verification_context)
                display_verification(verification, result.get("answer", ""))

            step_history = self._build_step_history(plan)
            final_decision = final_review(verification.recommendation, bool(step_history))

            if final_decision == "accept":
                return self._finalize(result, verification, plan)
            elif final_decision == "reject":
                console.print("[yellow]Answer rejected.[/yellow]")
                return {"answer": None, "status": "rejected"}
            elif final_decision == "revise":
                revised = self._handle_revision(query, plan, step_history)
                if revised:
                    result = revised
                    verification = None
            elif final_decision == "replan":
                replan_result = self._handle_replan(query, step_history)
                if replan_result:
                    result = replan_result["result"]
                    plan = replan_result["plan"]
                    verification = None
            elif final_decision is None:
                console.print("[yellow]Operation cancelled.[/yellow]")
                return {"answer": None, "status": "cancelled"}

    def _modify_plan(self, plan: Plan) -> Plan:
        """Allow user to modify plan steps."""
        for step in plan.steps:
            new_action = modify_plan_step(step.step, step.action)
            if new_action and new_action != step.action:
                step.action = new_action
                step.modified = True
        return plan

    def _sensemaking_loop(self, query: str, plan: Plan) -> dict[str, Any]:
        """Run sensemaking loop with progress display."""
        iteration = 0
        new_info: InfoSeekerResult | None = None

        while iteration < self.config.max_iterations:
            iteration += 1
            console.print(f"\n[bold cyan]═══ Iteration {iteration}/{self.config.max_iterations} ═══[/bold cyan]")

            # Show current step states
            if self.sensemaker._step_states:
                display_step_states(self.sensemaker._step_states, plan)

            sensemaker_result = self.sensemaker.process(query, plan, new_info)

            if sensemaker_result.status == "complete":
                console.print("\n[bold green]✓ Analysis complete![/bold green]")
                display_memory_table(self.memory.export())
                return {
                    "answer": sensemaker_result.answer,
                    "supporting_evidence": sensemaker_result.supporting_evidence,
                }

            # Show what sensemaker is requesting
            console.print(f"\n[bold]Sensemaker Request:[/bold] {sensemaker_result.request}")
            if sensemaker_result.reasoning:
                console.print(f"[dim]Reasoning: {sensemaker_result.reasoning}[/dim]")

            # Execute information seeking
            new_info = self._seek_with_retries(query, sensemaker_result.request)

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

        # Store failure in memory
        self.memory.update({
            "content": {
                "type": "execution_failure",
                "original_request": info_request,
                "attempts": self.config.max_retries,
                "errors": [e["error"] for e in error_history],
            }
        })

        assert new_info is not None
        return new_info

    def _build_step_history(self, plan: Plan) -> list[dict]:
        """Build list of plan steps with their execution results."""
        memory = self.memory.export()
        step_executions: dict[int, dict] = {}

        for entry in memory.get("entries", []):
            content = entry.get("content", {})
            if isinstance(content, dict) and "step" in content:
                step_num = content.get("step")
                step_executions[step_num] = {
                    "code": content.get("code", ""),
                    "result": content.get("result") or content.get("error", ""),
                    "success": content.get("success", False),
                    "source": content.get("source"),
                }

        history = []
        for plan_step in plan.steps:
            execution = step_executions.get(plan_step.step, {})
            history.append({
                "step": plan_step.step,
                "action": plan_step.action,
                "source": execution.get("source", plan_step.source),
                "code": execution.get("code", ""),
                "result": execution.get("result", "Not executed"),
                "success": execution.get("success", False),
            })
        return history

    def _build_step_context_for_info_seeker(self, plan: Plan) -> dict[str, Any]:
        """
        Build context about previous step results for the InformationSeekingAgent.

        This allows user-added steps to reference previous results like
        "subtract 10 from step 3 result".
        """
        step_results = {}
        memory = self.memory.export()

        for entry in memory.get("entries", []):
            content = entry.get("content", {})
            if isinstance(content, dict) and "step" in content:
                step_num = content.get("step")
                if content.get("success"):
                    step_results[f"step_{step_num}"] = {
                        "result": content.get("result"),
                        "action": None,  # Will fill from plan
                    }

        # Add action descriptions from plan
        for plan_step in plan.steps:
            key = f"step_{plan_step.step}"
            if key in step_results:
                step_results[key]["action"] = plan_step.action

        return {
            "previous_step_results": step_results,
            "instructions": (
                "The user is adding a new step that may reference previous results. "
                "Use the values from previous_step_results when the user says things like "
                "'step 3 result' or 'the result'. For example, if step_3 result is 156.0, "
                "and user says 'subtract 10 from step 3 result', compute: result = 156.0 - 10"
            ),
        }

    def _handle_revision(self, query: str, plan: Plan, step_history: list[dict]) -> dict[str, Any] | None:
        """Handle user revision of a specific step or adding a new step."""
        selection = select_step_to_revise(step_history)
        if selection is None:
            return None

        # Handle adding a new step
        if selection == "add_new":
            return self._handle_add_new_step(query, plan)

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

        return self._sensemaking_loop(query, plan)

    def _handle_add_new_step(self, query: str, plan: Plan) -> dict[str, Any] | None:
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
        step_context = self._build_step_context_for_info_seeker(plan)

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
        memory_entry = new_info.to_memory_entry(new_step_num)
        self.memory.update({"content": memory_entry.model_dump()})

        # Mark step as completed in sensemaker's state
        self.sensemaker.mark_step_completed(
            new_step_num,
            new_info.results if new_info.success else None,
            new_info.results if not new_info.success else None,
        )

        # Continue sensemaking with the updated plan
        return self._sensemaking_loop(query, plan)

    def _handle_replan(
        self, query: str, step_history: list[dict]
    ) -> dict[str, Any] | None:
        """
        Handle user request to replan while keeping successful results.

        Uses prompt engineering to pass previous results and suggested fix
        to the regular planner, then restarts the full loop.

        Args:
            query: The original user query.
            step_history: List of step execution results.

        Returns:
            Dict with new result and plan, or None if cancelled.
        """
        # Get optional suggested fix from user
        suggested_fix = get_replan_suggestion()
        if suggested_fix is None:
            return None

        console.print("\n[cyan]Creating new plan with learnings from previous attempt...[/cyan]\n")

        # Build replan context from memory and step history
        replan_context = self._build_replan_context(step_history, suggested_fix)

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
                new_plan = self._modify_plan(new_plan)
            elif decision is None:
                console.print("[yellow]Operation cancelled.[/yellow]")
                return None

        # Clear memory for fresh start (learnings are in the plan context)
        self.memory.clear()
        self.sensemaker.reset()

        # Execute the new plan
        console.print("\n[bold]Executing revised plan...[/bold]\n")
        new_result = self._sensemaking_loop(query, new_plan)

        return {"result": new_result, "plan": new_plan}

    def _build_replan_context(
        self, step_history: list[dict], suggested_fix: str | None
    ) -> str:
        """
        Build context string for replanning with learnings from previous attempt.

        Args:
            step_history: List of step execution results.
            suggested_fix: Optional user-provided guidance.

        Returns:
            Formatted context string to append to available sources.
        """
        context_parts = [
            "\n## LEARNINGS FROM PREVIOUS ATTEMPT",
            "A previous plan was executed but did not fully answer the question.",
            "Use these learnings to inform a COMPLETELY DIFFERENT approach.\n",
        ]

        # Extract learnings (facts discovered), not "results to reuse"
        learnings = []
        for step in step_history:
            action = step.get("action", "Unknown")
            result = step.get("result", "No result")
            success = step.get("success", False)

            if success:
                learnings.append(f"- {action} → Result: {result[:200]}")
            else:
                learnings.append(f"- {action} → FAILED: {result[:200]}")

        context_parts.append("### What was attempted and discovered:")
        context_parts.extend(learnings)
        context_parts.append("")

        if suggested_fix and suggested_fix.strip():
            context_parts.append("### USER FEEDBACK (important):")
            context_parts.append(suggested_fix)
            context_parts.append("")

        context_parts.append(
            "IMPORTANT: Create a FRESH plan. Do NOT simply repeat the previous "
            "approach with minor variations. Consider completely different methods "
            "or data sources if the previous approach was fundamentally flawed."
        )

        return "\n".join(context_parts)

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
            "step_results": self.sensemaker.step_results,
            "memory": self.memory.export(),
        }
