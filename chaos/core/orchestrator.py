"""Main orchestrator that coordinates the multi-agent pipeline."""

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
from ..tools.registry import ToolRegistry
from ..types import InfoSeekerResult, Plan, Verification
from .config import Config
from .logger import format_memory_state, format_plan, get_logger


class Orchestrator:
    """
    Orchestrates the multi-agent sensemaking pipeline.

    Flow:
    1. Planner creates execution plan from user query
    2. Sensemaker + InformationSeeker loop until COMPLETE
    3. Verifier validates the answer
    4. Return result (human-in-the-loop can be added later)
    """

    def __init__(
        self,
        config: Config,
        llm_client: StructuredLLMClient,
        tool_registry: ToolRegistry | None = None,
        data_registry: DataRegistry | None = None,
    ) -> None:
        self.config = config
        self.llm_client = llm_client
        self.tool_registry = tool_registry or ToolRegistry()
        self.data_registry = data_registry or DataRegistry()
        self.memory = Memory()

        # Initialize loggers
        self._orch_logger = get_logger("Orchestrator")
        self._planner_logger = get_logger("Planner")
        self._sensemaker_logger = get_logger("Sensemaker")
        self._verifier_logger = get_logger("Verifier")

        # Initialize agents with LLM client
        self.planner = PlannerAgent(config, llm_client)
        self.sensemaker = SensemakerAgent(config, llm_client, self.memory)
        self.info_seeker = InformationSeekingAgent(
            config, llm_client, self.tool_registry, self.data_registry
        )
        self.verifier = VerifierAgent(config, llm_client)

    def run(self, query: str) -> dict[str, Any]:
        """
        Execute the full pipeline for a user query.

        Args:
            query: The user's natural language query.

        Returns:
            Final result dictionary with answer and metadata.
        """
        # Reset memory and step tracking for new query
        self.memory.clear()
        self.sensemaker.reset()

        self._orch_logger.info(f"Processing query: {query}")

        # Step 1: Create execution plan
        self._planner_logger.debug("Creating execution plan...")

        available_sources = self.data_registry.get_sources_prompt()
        plan = self.planner.create_plan(query, available_sources)

        self._planner_logger.info(format_plan(plan))

        # Step 2: Sensemaking loop
        result = self._sensemaking_loop(query, plan)

        # Step 3: Verify the result with full context
        self._verifier_logger.debug("Verifying answer...")

        # Include plan and step results for better verification
        verification_context = {
            "plan": plan,
            "step_results": self.sensemaker._step_results,
            "memory": self.memory.export(),
        }

        # Log what the verifier will see
        self._verifier_logger.info(self._format_verifier_input(query, result, verification_context))

        verification = self.verifier.verify(query, result, verification_context)

        self._verifier_logger.info(f"Recommendation: {verification.recommendation}")
        self._verifier_logger.debug(self.verifier.generate_report(verification))

        return self._finalize(result, verification, plan)

    def _sensemaking_loop(
        self,
        query: str,
        plan: Plan,
    ) -> dict[str, Any]:
        """Execute the sensemaker-information seeker loop."""
        iteration = 0
        new_info: InfoSeekerResult | None = None
        result = {"answer": "", "supporting_evidence": []}

        while iteration < self.config.max_iterations:
            iteration += 1

            self._sensemaker_logger.info(
                f"=== Iteration {iteration}/{self.config.max_iterations} ==="
            )

            # Sensemaker processes current state (updates memory with new_info)
            sensemaker_result = self.sensemaker.process(query, plan, new_info)

            # Log memory state AFTER processing (so it reflects updated memory)
            self._sensemaker_logger.debug(format_memory_state(self.memory.export()))

            if sensemaker_result.status == "complete":
                self._sensemaker_logger.info("Task complete!")
                result = {
                    "answer": sensemaker_result.answer,
                    "supporting_evidence": sensemaker_result.supporting_evidence,
                }
                break

            # Need more information (sensemaker_result is NeedsInfoResponse)
            info_request = sensemaker_result.request
            reasoning = sensemaker_result.reasoning
            if reasoning:
                self._sensemaker_logger.info(f"Information needed: {info_request}")
                self._sensemaker_logger.debug(f"Reasoning: {reasoning}")
            else:
                self._sensemaker_logger.info(f"Information needed: {info_request}")

            if not info_request:
                self._sensemaker_logger.warning("No specific info request, ending loop")
                break

            # Information seeker retrieves data with retry logic
            new_info = self._seek_with_retries(query, info_request)

        # If we hit max iterations without completing, try to get best answer
        if iteration >= self.config.max_iterations and not result.get("answer"):
            self._orch_logger.warning("Max iterations reached, getting best answer...")
            final_result = self.sensemaker.get_answer()
            result = {
                "answer": final_result.answer,
                "supporting_evidence": final_result.supporting_evidence,
            }

        return result

    def _seek_with_retries(
        self,
        query: str,
        info_request: str,
    ) -> InfoSeekerResult:
        """
        Seek information with retry logic and sensemaker guidance on failure.

        Args:
            query: Original user query.
            info_request: The information request from sensemaker.

        Returns:
            InfoSeekerResult with retrieved information.
        """
        error_history: list[dict[str, Any]] = []
        current_request = info_request
        new_info: InfoSeekerResult | None = None

        for attempt in range(self.config.max_retries):
            new_info = self.info_seeker.seek(current_request)

            if new_info.success:
                return new_info

            # Collect error for history
            error_entry = {
                "attempt": attempt + 1,
                "request": current_request,
                "error": new_info.results,  # Results contain error message on failure
            }
            error_history.append(error_entry)

            self._orch_logger.warning(
                f"InfoSeeker attempt {attempt + 1}/{self.config.max_retries} failed: "
                f"{error_entry['error']}"
            )

            # If not the last retry, get guidance from sensemaker
            if attempt < self.config.max_retries - 1:
                self._sensemaker_logger.debug(
                    "Consulting sensemaker for recovery guidance..."
                )

                available_sources = self.data_registry.get_sources_prompt()
                recovery = self.sensemaker.guide_recovery(
                    query=query,
                    original_request=info_request,
                    error_history=error_history,
                    available_sources=available_sources,
                )

                self._sensemaker_logger.info(f"Recovery summary: {recovery.summary}")
                self._sensemaker_logger.debug(f"Analysis: {recovery.analysis}")
                self._sensemaker_logger.info(
                    f"Revised request: {recovery.revised_request}"
                )

                # Use the revised request for the next attempt
                current_request = recovery.revised_request or current_request

        # All retries exhausted - return last failure with accumulated context
        self._orch_logger.error(
            f"InfoSeeker failed after {self.config.max_retries} attempts"
        )

        # Store failure summary in memory
        self.memory.update({
            "content": {
                "type": "execution_failure",
                "original_request": info_request,
                "attempts": self.config.max_retries,
                "errors": [e["error"] for e in error_history],
                "final_status": "exhausted_retries",
            }
        })

        # new_info is guaranteed to be set after at least one iteration
        assert new_info is not None
        return new_info

    def _format_verifier_input(
        self,
        query: str,
        result: dict[str, Any],
        context: dict[str, Any],
    ) -> str:
        """Format the input being sent to the verifier for logging."""
        lines = ["Verifier Input:"]
        lines.append(f"  Query: {query}")
        lines.append(f"  Answer: {result.get('answer', 'N/A')}")

        # Show memory entries as evidence (code + results)
        memory = context.get("memory", {})
        entries = memory.get("entries", [])
        if entries:
            lines.append("  Evidence (from memory):")
            for entry in entries:
                content = entry.get("content", {})
                if isinstance(content, dict) and "code" in content:
                    step = content.get("step", "?")
                    source = content.get("source", "unknown")
                    code = content.get("code", "")
                    if content.get("success") and "result" in content:
                        lines.append(f"    Step {step} ({source}):")
                        lines.append(f"      Code: {code}")
                        lines.append(f"      Result: {content['result']}")
                    elif "error" in content:
                        lines.append(f"    Step {step} ({source}):")
                        lines.append(f"      Code: {code}")
                        lines.append(f"      Error: {content['error']}")

        plan = context.get("plan")
        if plan is not None and isinstance(plan, Plan) and plan.steps:
            lines.append("  Plan Steps:")
            for step in plan.steps:
                lines.append(f"    Step {step.step}: {step.action}")

        return "\n".join(lines)

    def _finalize(
        self,
        result: dict[str, Any],
        verification: Verification,
        plan: Plan | None = None,
        max_iterations_reached: bool = False,
    ) -> dict[str, Any]:
        """Prepare final output."""
        # Use verifier's confidence_score as the final confidence
        confidence = verification.confidence_score

        return {
            "answer": result.get("answer"),
            "confidence": confidence,
            "supporting_evidence": result.get("supporting_evidence", []),
            "verification": verification.model_dump(),
            "plan": plan.model_dump() if plan else None,
            "step_results": self.sensemaker._step_results,
            "memory": self.memory.export(),
            "max_iterations_reached": max_iterations_reached,
        }
