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
    - Success criteria
    """

    def __init__(self, config: Config, llm_client: StructuredLLMClient) -> None:
        super().__init__(config, llm_client)
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

CRITICAL: AVOID RETURNING RAW DATA LISTS

When creating plans, follow these rules to prevent memory overflow:

1. AGGREGATION QUERIES (average, sum, count, min, max, std):
   - Create ONE step that computes the result directly
   - Combine filtering with aggregation in a single step
   - Example: "Compute average heart_rate where uid='test004'"

2. NEVER create intermediate steps that return:
   - Filtered DataFrames (can be millions of rows)
   - Lists of values (can be millions of items)
   - Raw record extractions

3. ONLY return individual records when:
   - User explicitly asks for "list all", "show me each", etc.
   - The query is about specific individual items
   - You limit results (e.g., "first 10 records")

4. For multiple statistics, compute them in ONE step:
   - Example: "Compute min, max, and average heart_rate where uid='test004'"

BAD PLAN for "What is the average heart rate of test004?":
  Step 1: Filter records where uid='test004'  <- Returns potentially millions of rows!
  Step 2: Extract heart_rate column           <- Returns list of millions of values!
  Step 3: Compute average                     <- Finally computes

GOOD PLAN:
  Step 1: Compute average heart_rate where uid='test004'  <- Single value result

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
        plan.query = query  # Set the original query
        return plan
