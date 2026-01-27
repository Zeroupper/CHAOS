"""Information seeking agent - retrieves data from sources."""

import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import pandas as pd

from ..core.config import Config
from ..core.logger import format_code, format_result
from ..data.registry import DataRegistry
from ..llm.structured_client import StructuredLLMClient
from ..types import ExecutionResult, InfoSeekerResult, QueryDecision
from .base import BaseAgent


class InformationSeekingAgent(BaseAgent):
    """
    Seeks information from data sources and tools.

    Responsibilities:
    - Interpret information requests from sensemaker
    - Query appropriate data sources
    - Execute tools when needed
    - Return structured results
    """

    def __init__(
        self,
        config: Config,
        llm_client: StructuredLLMClient,
        data_registry: DataRegistry,
    ) -> None:
        super().__init__(config, llm_client)
        self.data_registry = data_registry
        self._system_prompt = """You are an information seeking agent. Write Python code to extract the needed information from datasets.

You will be provided with detailed schema information about available datasets including column names, types, units, and value ranges. Use this information to write accurate queries.

AVAILABLE VARIABLES:
- `df`: The primary data source DataFrame (specified in "source" field)
- ALL data sources are also available by name (e.g., `garmin_ibi`, `garmin_stress`, `garmin_hr`)
- `pd`: pandas library
- `np`: numpy library

This means you can join multiple data sources in a single query!

IMPORTANT RULES:

1. USE PROVIDED VALUES FROM PREVIOUS STEPS:
   - If the request includes values from previous steps (e.g., "Using average=78.5 and maximum=155.0")
   - Use these values DIRECTLY in your code - do NOT recalculate them from the DataFrame
   - Example: "result = round((78.5 / 2 + 155.0 / 2), 2)" NOT "result = round((df['x'].mean() / 2 + df['x'].max() / 2), 2)"

2. For data extraction (no previous values provided):
   - Use exact column names from the schema (e.g., 'heart_rate' not 'hr')
   - Always compute aggregated results (mean, sum, count, etc.), never return raw data
   - Keep results small and focused

3. FOLLOW EXACT PARAMETERS:
   - If the request specifies "round to 5 decimal places", use round(..., 5), NOT round(..., 2)
   - If the request specifies a specific format or precision, follow it exactly
   - Pay close attention to numerical parameters in the request text

4. MULTI-SOURCE QUERIES:
   - You can access any data source directly by its name (e.g., `garmin_ibi`, `garmin_stress`)
   - For joins: use pd.merge(garmin_ibi, garmin_stress, on='uid')
   - The "source" field should be the primary source you're working with

5. General:
   - Store your final answer in the `result` variable

Examples:
- Using previous values: result = round((78.50438924168846 / 2 + 155.0 / 2), 2)
- Average: result = df['heart_rate'].mean()
- Filtered average: result = df[df['uid'] == 'test004']['heart_rate'].mean()
- Count: result = len(df)
- Sum: result = df['steps'].sum()
- Multiple stats: result = {'mean': df['heart_rate'].mean(), 'max': df['heart_rate'].max()}
- Multi-source join: result = pd.merge(garmin_ibi, garmin_stress, on=['uid', 'timestamp'])

Respond with a JSON object:
{
    "source": "primary_dataset_name",
    "query_type": "exec",
    "params": {"code": "result = ..."}
}

NOTE: For pure computations using provided values (no DataFrame access needed), still specify a source but the code won't use df."""

    def execute(
        self,
        info_request: str,
        context: dict[str, Any] | None = None,
    ) -> InfoSeekerResult:
        """
        Seek information based on request.

        Args:
            info_request: Description of information needed.
            context: Additional context from sensemaker.

        Returns:
            InfoSeekerResult with retrieved information.
        """
        return self.seek(info_request, context)

    def seek(
        self,
        info_request: str,
        context: dict[str, Any] | None = None,
    ) -> InfoSeekerResult:
        """Seek information from available sources."""
        self._logger.debug(f"Seeking: {info_request}")

        # Get available sources info
        sources_info = self._get_sources_info()

        # Ask LLM what to query
        try:
            query_decision = self._decide_query(info_request, sources_info, context)
        except Exception as e:
            self._logger.error(f"Failed to decide query: {e}")
            return InfoSeekerResult(
                request=info_request,
                source="unknown",
                query_type="exec",
                params={},
                results=f"LLM failed to generate query: {e}",
                success=False,
            )

        # Execute the query
        source_name = query_decision.source
        query_type = query_decision.query_type
        params = query_decision.params

        # Log code execution
        if query_type == "exec" and "code" in params:
            self._logger.info(
                f"Executing on {source_name}:\n{format_code(params['code'])}"
            )
        else:
            self._logger.debug(f"Querying {source_name} with {query_type}")

        exec_result = self._execute_query(source_name, query_type, params)

        # Filter params to only include string values (exclude internal params like all_sources)
        filtered_params = {k: v for k, v in params.items() if isinstance(v, str)}

        # Log results
        if exec_result.error:
            self._logger.error(f"Query failed: {exec_result.error}")
            return InfoSeekerResult(
                request=info_request,
                source=source_name,
                query_type=query_type,
                params=filtered_params,
                results=exec_result.error,
                success=False,
            )
        else:
            result_str = exec_result.result or ""
            self._logger.info(f"Result: {format_result(result_str)}")
            return InfoSeekerResult(
                request=info_request,
                source=source_name,
                query_type=query_type,
                params=filtered_params,
                results=result_str,
                success=True,
            )

    def _get_sources_info(self) -> str:
        """Get formatted information about available data sources."""
        sources = self.data_registry.list_sources()
        if not sources:
            return "No data sources available."

        lines = ["Available data sources:"]
        for source in sources:
            lines.append(f"\n- {source['name']}: {source['description']}")
            schema = source.get("schema", {})
            if schema.get("columns"):
                cols = schema["columns"][:15]  # Limit to first 15 columns
                lines.append(f"  Columns: {', '.join(cols)}")
                if len(schema["columns"]) > 15:
                    lines.append(f"  ... and {len(schema['columns']) - 15} more columns")
            if schema.get("row_count"):
                lines.append(f"  Rows: {schema['row_count']}")

        return "\n".join(lines)

    def _decide_query(
        self,
        info_request: str,
        sources_info: str,
        context: dict[str, Any] | None,
    ) -> QueryDecision:
        """Use LLM to decide which query to execute."""
        context_str = ""
        if context:
            context_str = f"\nAdditional context:\n{json.dumps(context, indent=2)}"

        prompt = f"""I need to find the following information:

{info_request}

{sources_info}
{context_str}

What query should I execute? Respond with JSON specifying the source, query_type, and params."""

        messages = [{"role": "user", "content": prompt}]
        return self._call_llm(messages, QueryDecision)

    def _execute_query(
        self, source_name: str, query_type: str, params: dict[str, str]
    ) -> ExecutionResult:
        """Execute a query on a data source."""
        # Handle multi-source references (e.g., "garmin_ibi + garmin_stress")
        # Use the first source as primary, but inject all sources
        primary_source_name = source_name.split("+")[0].split(",")[0].strip()

        source = self.data_registry.get(primary_source_name)
        if source is None:
            return ExecutionResult(error=f"Data source '{primary_source_name}' not found")

        try:
            # Collect all data sources to inject into execution namespace
            all_sources = self._get_all_source_dataframes()

            # Create execution params (don't modify original params dict)
            exec_params: dict[str, Any] = {**params, "all_sources": all_sources}

            return source.query(query_type, **exec_params)
        except Exception as e:
            return ExecutionResult(error=str(e))

    def _get_all_source_dataframes(self) -> dict[str, Any]:
        """Get all data source DataFrames for multi-source queries."""
        all_sources: dict[str, Any] = {}

        for source_info in self.data_registry.list_sources():
            source_name = source_info["name"]
            source = self.data_registry.get(source_name)
            if source is not None:
                try:
                    source.connect()
                    if hasattr(source, "_data") and source._data is not None:
                        all_sources[source_name] = source._data
                except Exception as e:
                    self._logger.warning(f"Failed to load source '{source_name}': {e}")

        return all_sources
