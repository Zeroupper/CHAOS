"""Main orchestrator that coordinates the multi-agent pipeline."""

from typing import Any

from ..agents import (
    InformationSeekingAgent,
    PlannerAgent,
    SensemakerAgent,
    VerifierAgent,
)
from ..data.registry import DataRegistry
from ..llm import LLMClient
from ..memory import Memory
from ..tools.registry import ToolRegistry
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
        llm_client: LLMClient,
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
        # Reset memory for new query
        self.memory.clear()

        self._orch_logger.info(f"Processing query: {query}")

        # Step 1: Create execution plan
        self._planner_logger.debug("Creating execution plan...")

        available_sources = self.data_registry.get_sources_prompt()
        plan = self.planner.create_plan(query, available_sources)

        self._planner_logger.info(format_plan(plan))

        # Step 2: Sensemaking loop
        result = self._sensemaking_loop(query, plan)

        # Step 3: Verify the result
        self._verifier_logger.debug("Verifying answer...")

        verification = self.verifier.verify(query, result)

        self._verifier_logger.info(f"Recommendation: {verification.get('recommendation')}")
        self._verifier_logger.debug(self.verifier.generate_report(verification))

        return self._finalize(result, verification)

    def _sensemaking_loop(
        self,
        query: str,
        plan: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute the sensemaker-information seeker loop."""
        iteration = 0
        new_info = None
        result = {"answer": "", "confidence": 0.0, "supporting_evidence": []}

        while iteration < self.config.max_iterations:
            iteration += 1

            self._sensemaker_logger.info(
                f"=== Iteration {iteration}/{self.config.max_iterations} ==="
            )

            # Log memory state at DEBUG level
            self._sensemaker_logger.debug(format_memory_state(self.memory.export()))

            # Sensemaker processes current state
            sensemaker_result = self.sensemaker.process(query, plan, new_info)

            if sensemaker_result.get("status") == "complete":
                self._sensemaker_logger.info("Task complete!")
                result = {
                    "answer": sensemaker_result.get("answer", ""),
                    "confidence": sensemaker_result.get("confidence", 0.0),
                    "supporting_evidence": sensemaker_result.get(
                        "supporting_evidence", []
                    ),
                }
                break

            # Need more information
            info_request = sensemaker_result.get("request", "")
            reasoning = sensemaker_result.get("reasoning", "")
            if reasoning:
                self._sensemaker_logger.info(f"Information needed: {info_request}")
                self._sensemaker_logger.debug(f"Reasoning: {reasoning}")
            else:
                self._sensemaker_logger.info(f"Information needed: {info_request}")

            if not info_request:
                self._sensemaker_logger.warning("No specific info request, ending loop")
                break

            # Information seeker retrieves data (logged internally by the agent)
            new_info = self.info_seeker.seek(info_request)

            success = new_info.get("success", False)
            if not success:
                self._orch_logger.warning(
                    f"InfoSeeker failed: {new_info.get('error', 'Unknown')}"
                )

        # If we hit max iterations without completing, try to get best answer
        if iteration >= self.config.max_iterations and not result.get("answer"):
            self._orch_logger.warning("Max iterations reached, getting best answer...")
            final_result = self.sensemaker.get_answer()
            result = {
                "answer": final_result.get("answer", "Could not complete analysis"),
                "confidence": final_result.get("confidence", 0.0),
                "supporting_evidence": final_result.get("supporting_evidence", []),
            }

        return result

    def _finalize(
        self,
        result: dict[str, Any],
        verification: dict[str, Any],
        max_iterations_reached: bool = False,
    ) -> dict[str, Any]:
        """Prepare final output."""
        return {
            "answer": result.get("answer"),
            "confidence": result.get("confidence", 0.0),
            "supporting_evidence": result.get("supporting_evidence", []),
            "verification": verification,
            "memory": self.memory.export(),
            "max_iterations_reached": max_iterations_reached,
        }
