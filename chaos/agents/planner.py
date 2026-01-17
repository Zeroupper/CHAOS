"""Planner agent - creates execution plans from user queries."""

from typing import Any

from ..core.config import Config
from .base import BaseAgent


class PlannerAgent(BaseAgent):
    """
    Creates an execution plan based on user query.

    The planner analyzes the query and determines:
    - What information is needed
    - Which data sources to query
    - What steps to take
    - Success criteria
    """

    def __init__(self, config: Config) -> None:
        super().__init__(config)
        self._system_prompt = """You are a planning agent. Your task is to create
        a detailed execution plan for answering user queries about data.

        Output a structured plan with:
        1. Query understanding
        2. Required information
        3. Data sources to query
        4. Step-by-step approach
        5. Success criteria
        """

    def execute(self, query: str) -> dict[str, Any]:
        """Create an execution plan for the query."""
        return self.create_plan(query)

    def create_plan(self, query: str) -> dict[str, Any]:
        """
        Create an execution plan for the given query.

        Args:
            query: The user's natural language query.

        Returns:
            Structured plan dictionary.
        """
        # TODO: Implement plan creation
        plan = {
            "query": query,
            "understanding": "",
            "required_info": [],
            "data_sources": [],
            "steps": [],
            "success_criteria": [],
        }
        return plan
