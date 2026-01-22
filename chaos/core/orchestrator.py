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

        if self.config.verbose:
            print(f"\n[Orchestrator] Processing query: {query}")

        # Step 1: Create execution plan
        if self.config.verbose:
            print("\n[Planner] Creating execution plan...")

        available_sources = self.data_registry.get_sources_prompt()
        plan = self.planner.create_plan(query, available_sources)

        if self.config.verbose:
            print(f"[Planner] Plan created: {plan.get('query_understanding', 'N/A')}")

        # Step 2: Sensemaking loop
        result = self._sensemaking_loop(query, plan)

        # Step 3: Verify the result
        if self.config.verbose:
            print("\n[Verifier] Verifying answer...")

        verification = self.verifier.verify(query, result)

        if self.config.verbose:
            print(f"[Verifier] Recommendation: {verification.get('recommendation')}")
            print(self.verifier.generate_report(verification))

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

            if self.config.verbose:
                print(f"\n[Sensemaker] Iteration {iteration}/{self.config.max_iterations}")

            # Sensemaker processes current state
            sensemaker_result = self.sensemaker.process(query, plan, new_info)

            if sensemaker_result.get("status") == "complete":
                if self.config.verbose:
                    print("[Sensemaker] Task complete!")
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
            if self.config.verbose:
                print(f"[Sensemaker] Needs info: {info_request}")

            if not info_request:
                if self.config.verbose:
                    print("[Sensemaker] No specific info request, ending loop")
                break

            # Information seeker retrieves data
            if self.config.verbose:
                print(f"[InfoSeeker] Seeking: {info_request}")

            new_info = self.info_seeker.seek(info_request)

            if self.config.verbose:
                success = new_info.get("success", False)
                print(f"[InfoSeeker] Success: {success}")
                if not success:
                    print(f"[InfoSeeker] Error: {new_info.get('error', 'Unknown')}")

        # If we hit max iterations without completing, try to get best answer
        if iteration >= self.config.max_iterations and not result.get("answer"):
            if self.config.verbose:
                print("[Orchestrator] Max iterations reached, getting best answer...")
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
