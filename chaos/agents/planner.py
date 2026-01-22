"""Planner agent - creates execution plans from user queries."""

from typing import Any

from ..core.config import Config
from ..llm import LLMClient
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

    def __init__(self, config: Config, llm_client: LLMClient) -> None:
        super().__init__(config, llm_client)
        self._system_prompt = """You are a planning agent for a data analysis system. Your task is to create detailed execution plans for answering user queries about datasets.

You have access to various data sources containing health and activity data. When creating a plan, analyze the query carefully and determine what information needs to be gathered.

Always respond with a JSON object in the following format:
{
    "query_understanding": "Your interpretation of what the user is asking",
    "required_info": ["List of specific pieces of information needed"],
    "data_sources": ["List of data source names to query"],
    "steps": [
        {"step": 1, "action": "Description of action", "source": "data_source_name"},
        {"step": 2, "action": "Description of action", "source": "data_source_name"}
    ],
    "success_criteria": ["Criteria for determining when the question is answered"]
}

Be specific and actionable in your plan."""

    def execute(self, query: str, available_sources: str = "") -> dict[str, Any]:
        """Create an execution plan for the query."""
        return self.create_plan(query, available_sources)

    def create_plan(
        self, query: str, available_sources: str = ""
    ) -> dict[str, Any]:
        """
        Create an execution plan for the given query.

        Args:
            query: The user's natural language query.
            available_sources: Description of available data sources.

        Returns:
            Structured plan dictionary.
        """
        prompt = f"""Create an execution plan for the following query:

Query: {query}

{available_sources}

Respond with a JSON plan."""

        messages = [{"role": "user", "content": prompt}]
        response = self._call_llm(messages)
        plan = self._parse_response(response)

        # Ensure required fields exist
        plan.setdefault("query", query)
        plan.setdefault("query_understanding", "")
        plan.setdefault("required_info", [])
        plan.setdefault("data_sources", [])
        plan.setdefault("steps", [])
        plan.setdefault("success_criteria", [])

        return plan
