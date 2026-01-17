"""Sensemaker agent - updates memory and synthesizes information."""

from typing import Any

from ..core.config import Config
from ..memory import Memory
from .base import BaseAgent


class SensemakerAgent(BaseAgent):
    """
    Updates its memory based on information from the InformationSeekingAgent.

    Responsibilities:
    - Process incoming information
    - Update working memory
    - Synthesize understanding
    - Decide when task is COMPLETE
    """

    def __init__(self, config: Config, memory: Memory) -> None:
        super().__init__(config)
        self.memory = memory
        self._system_prompt = """You are a sensemaking agent. Your task is to:
        1. Process information retrieved by the information seeking agent
        2. Update your understanding of the problem
        3. Synthesize insights from multiple data sources
        4. Determine when you have enough information to answer the query

        When you have sufficient information, respond with COMPLETE.
        Otherwise, specify what additional information is needed.
        """

    def execute(
        self,
        query: str,
        plan: dict[str, Any],
        new_info: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Process information and update understanding.

        Args:
            query: Original user query.
            plan: Execution plan from planner.
            new_info: New information from information seeker.

        Returns:
            Status dict with 'complete' flag and current understanding.
        """
        return self.process(query, plan, new_info)

    def process(
        self,
        query: str,
        plan: dict[str, Any],
        new_info: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Process new information and update memory."""
        if new_info:
            self.memory.update(new_info)

        # TODO: Implement synthesis logic
        return {
            "complete": False,
            "answer": None,
            "next_info_needed": "",
            "current_understanding": self.memory.get_summary(),
        }

    def get_answer(self) -> dict[str, Any]:
        """Generate final answer from accumulated knowledge."""
        # TODO: Implement answer generation
        return {
            "answer": "",
            "confidence": 0.0,
            "supporting_evidence": [],
        }
