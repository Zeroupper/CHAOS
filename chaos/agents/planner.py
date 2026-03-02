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

        self._system_prompt = """You are a planning agent for a data analysis system. Create execution plans for user queries about datasets.

Only plan for clear, specific questions. Return EMPTY steps for unclear or non-analytical queries.

GROUNDING — NO HALLUCINATION:
- The input contains a DATASET SCHEMAS section listing every dataset with exact column names and dtypes.
- The "source" field in each step MUST be an exact dataset name from the schemas.
- If a column is not listed in DATASET SCHEMAS, it does not exist.


STEP RESULTS — each step's output is automatically saved as `step_N_result`:
- Step 1 output → `step_1_result`, Step 2 output → `step_2_result`, etc.
- When a step depends on previous results, explicitly reference the variable in the action description.
- Example: "Compute correlation between heart_rate columns in step_1_result and step_2_result"

Use the data discoveries (actual column names, types, value formats) to select correct data sources, columns, and aggregations.

Respond with JSON:
{"query_understanding": "...", "required_info": ["..."], "data_sources": ["..."], "steps": [{"step": 1, "action": "...", "source": "..."}]}

Reference exact column names from the data discoveries."""

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

        context_block = data_context if data_context else available_sources

        prompt = f"""Create an execution plan for the following query:

Query: {query}

{context_block}

Respond with a JSON plan."""

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

        context_block = plan.data_context if plan.data_context else self._available_sources

        prompt = f"""Modify the following plan according to the user's instructions.

Current plan understanding: {plan.query_understanding}

Current steps:
{current_steps}

User's modification request: {feedback}

The user's request is AUTHORITATIVE. Apply exactly what they ask for.
Do NOT revert to any previous intent. Do NOT ignore or reinterpret the request.
Update the query_understanding to reflect the modified plan.

{context_block}

Respond with the revised JSON plan."""

        messages = [{"role": "user", "content": prompt}]
        revised = self._call_llm(messages, Plan)
        revised.query = plan.query
        revised.data_context = plan.data_context
        return revised
