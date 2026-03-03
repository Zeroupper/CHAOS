"""Planner agent - creates execution plans from user queries."""

from ..core.config import Config
from ..llm.structured_client import StructuredLLMClient
from ..types import Plan
from .base import BaseAgent


class PlannerAgent(BaseAgent):
    """
    Creates an execution plan based on user query.

    The planner analyzes the query and determines:
    - What information is needed
    - Which data sources to query
    - What steps to take

    Expects data_context (from ExplorerAgent) to be passed explicitly
    via create_plan() — the orchestrator owns the explorer→planner flow.
    """

    def __init__(
        self,
        config: Config,
        llm_client: StructuredLLMClient,
    ) -> None:
        super().__init__(config, llm_client)

        self._base_system_prompt = """Create step-by-step execution plans for data analysis queries.

RULES:
- Only use dataset names and column names from the DATASET SCHEMAS below.
- Each step output is saved as `step_N_result`. Reference it in later steps.
- Return EMPTY steps for unclear or non-analytical queries.

Respond with JSON:
{"query_understanding": "<str>", "steps": [{"step": <int>, "action": "<str: what to compute>", "source": "<str: dataset_name>"}]}"""

        self._system_prompt = self._base_system_prompt
        self._available_sources: str = ""

    def _build_system_prompt(self, data_context: str) -> None:
        """Set the system prompt with dataset schemas included."""
        context_block = data_context if data_context else self._available_sources
        if context_block:
            self._system_prompt = f"{self._base_system_prompt}\n\n{context_block}"
        else:
            self._system_prompt = self._base_system_prompt

    def create_plan(self, query: str, available_sources: str = "", data_context: str = "") -> Plan:
        """
        Create an execution plan for the given query.

        Args:
            query: The user's natural language query.
            available_sources: Description of available data sources.
            data_context: Exploration results from ExplorerAgent (schemas, discoveries).

        Returns:
            Plan object with steps and metadata.
        """
        self._available_sources = available_sources
        self._build_system_prompt(data_context)

        prompt = f"Create an execution plan for the following query:\n\n{query}"

        messages = [{"role": "user", "content": prompt}]
        plan = self._call_llm(messages, Plan)
        plan.query = query
        plan.data_context = data_context
        return plan

    def modify_plan(self, plan: Plan, feedback: str) -> Plan:
        """
        Modify a plan based on user feedback.

        Args:
            plan: The current plan.
            feedback: User's feedback on what to change.

        Returns:
            Updated Plan object.
        """
        current_steps = "\n".join(
            f"  Step {s.step}: {s.action} (source: {s.source or '-'})"
            for s in plan.steps
        )

        self._build_system_prompt(plan.data_context)

        prompt = f"""Modify the following plan according to the user's instructions.

Current plan understanding: {plan.query_understanding}

Current steps:
{current_steps}

User's modification request: {feedback}

The user's request is AUTHORITATIVE. Apply exactly what they ask for.
Do NOT revert to any previous intent. Do NOT ignore or reinterpret the request.
Update the query_understanding to reflect the modified plan.

Respond with the revised JSON plan."""

        messages = [{"role": "user", "content": prompt}]
        revised = self._call_llm(messages, Plan)
        revised.query = plan.query
        revised.data_context = plan.data_context
        return revised
