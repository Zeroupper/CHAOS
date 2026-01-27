"""Planner agent - creates execution plans from user queries."""

from ..core.config import Config
from ..llm.structured_client import StructuredLLMClient
from ..tools.base import BaseTool
from ..types import Plan
from .base import BaseAgent


class PlannerAgent(BaseAgent):
    """
    Creates an execution plan based on user query.

    The planner analyzes the query and determines:
    - What information is needed
    - Which data sources to query
    - What steps to take

    If web search tools are available, the planner will autonomously
    conduct a research phase - deciding whether to search, fetch URLs,
    or stop based on the accumulated context.
    """

    def __init__(
        self,
        config: Config,
        llm_client: StructuredLLMClient,
        tools: list[BaseTool] | None = None,
    ) -> None:
        super().__init__(config, llm_client, tools)

        self._system_prompt = """You are a planning agent for a data analysis system. Your task is to create detailed execution plans for answering user queries about datasets.

You will be provided with detailed schema information about available datasets including:
- Column names, types, and descriptions
- Units of measurement (e.g., bpm, ms, steps, meters)
- Typical value ranges
- Possible enum values for categorical columns
- Relationships between datasets (join keys)
- Analysis hints for common query patterns

Use this schema information to:
1. Select the most appropriate data sources for the query
2. Identify the correct column names and understand their meaning
3. Consider data relationships when queries span multiple datasets
4. Plan appropriate aggregations based on data types and units

STEP PLANNING RULES:

The key principle is: OPTIMIZE FOR RESULT SIZE, NOT STEP COUNT.
- Steps that return small results (single values, small aggregations) are FINE as separate steps
- Steps that return large results (filtered DataFrames, lists of values) must be combined with aggregation

1. SEPARATE STEPS ARE OK when each returns a small result:
   - Each aggregation (mean, max, min, sum, count) returns a single value - these can be separate steps
   - Final computation steps that combine previous results are separate steps

2. COMBINE STEPS when intermediate results would be large:
   - Filtering + aggregation should be ONE step (filter returns millions of rows)
   - Don't create a step that just filters data without aggregating

3. NEVER create steps that return:
   - Filtered DataFrames without aggregation (can be millions of rows)
   - Lists of raw values (can be millions of items)
   - Raw record extractions (unless explicitly limited)

Always respond with a JSON object in the following format:
{
    "query_understanding": "Your interpretation of what the user is asking",
    "required_info": ["List of specific pieces of information needed"],
    "data_sources": ["List of data source names to query"],
    "steps": [
        {"step": 1, "action": "Description of action", "source": "data_source_name"},
        {"step": 2, "action": "Description of action", "source": "data_source_name"}
    ]
}

Be specific and actionable. Reference exact column names from the schema."""

    def execute(self, query: str, available_sources: str = "") -> Plan:
        """Create an execution plan for the query."""
        return self.create_plan(query, available_sources)

    def create_plan(self, query: str, available_sources: str = "") -> Plan:
        """
        Create an execution plan for the given query.

        Args:
            query: The user's natural language query.
            available_sources: Description of available data sources.

        Returns:
            Plan object with steps and metadata.
        """
        prompt = f"""Create an execution plan for the following query:

Query: {query}

{available_sources}

Respond with a JSON plan."""

        messages = [{"role": "user", "content": prompt}]
        plan = self._call_llm(messages, Plan)
        plan.query = query
        return plan
