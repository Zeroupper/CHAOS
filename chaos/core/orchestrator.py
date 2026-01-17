"""Main orchestrator that coordinates the multi-agent pipeline."""

from typing import Any

from ..agents import (
    InformationSeekingAgent,
    PlannerAgent,
    SensemakerAgent,
    VerifierAgent,
)
from ..data.registry import DataRegistry
from ..memory import Memory
from ..tools.registry import ToolRegistry
from .config import Config


class Orchestrator:
    """
    Orchestrates the multi-agent sensemaking pipeline.

    Flow:
    1. Planner creates execution plan from user query
    2. Sensemaker + InformationSeeker loop until COMPLETE
    3. Verifier validates the answer
    4. Human reviews: approve / reject / add info
    5. If rejected, back to step 2 with feedback
    """

    def __init__(
        self,
        config: Config,
        tool_registry: ToolRegistry | None = None,
        data_registry: DataRegistry | None = None,
    ) -> None:
        self.config = config
        self.tool_registry = tool_registry or ToolRegistry()
        self.data_registry = data_registry or DataRegistry()
        self.memory = Memory()

        # Initialize agents
        self.planner = PlannerAgent(config)
        self.sensemaker = SensemakerAgent(config, self.memory)
        self.info_seeker = InformationSeekingAgent(
            config, self.tool_registry, self.data_registry
        )
        self.verifier = VerifierAgent(config)

    def run(self, query: str) -> dict[str, Any]:
        """
        Execute the full pipeline for a user query.

        Args:
            query: The user's natural language query.

        Returns:
            Final result dictionary with answer and metadata.
        """
        # Step 1: Create execution plan
        plan = self.planner.create_plan(query)

        iteration = 0
        human_feedback = None

        while iteration < self.config.max_iterations:
            # Step 2: Sensemaking loop
            result = self._sensemaking_loop(query, plan, human_feedback)

            # Step 3: Verify the result
            verification = self.verifier.verify(query, result)

            # Step 4: Human review
            human_decision = self._get_human_feedback(verification)

            if human_decision["action"] == "approve":
                return self._finalize(result, verification)
            elif human_decision["action"] == "reject":
                human_feedback = human_decision.get("feedback")
            else:  # add_info
                human_feedback = human_decision.get("additional_info")

            iteration += 1

        return self._finalize(result, verification, max_iterations_reached=True)

    def _sensemaking_loop(
        self,
        query: str,
        plan: dict[str, Any],
        feedback: str | None = None,
    ) -> dict[str, Any]:
        """Execute the sensemaker-information seeker loop."""
        # TODO: Implement the loop logic
        raise NotImplementedError

    def _get_human_feedback(self, verification: dict[str, Any]) -> dict[str, Any]:
        """Present verification to human and get feedback."""
        # TODO: Implement human-in-the-loop interface
        raise NotImplementedError

    def _finalize(
        self,
        result: dict[str, Any],
        verification: dict[str, Any],
        max_iterations_reached: bool = False,
    ) -> dict[str, Any]:
        """Prepare final output."""
        return {
            "answer": result.get("answer"),
            "verification": verification,
            "memory": self.memory.export(),
            "max_iterations_reached": max_iterations_reached,
        }
