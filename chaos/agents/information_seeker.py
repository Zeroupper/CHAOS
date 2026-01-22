"""Information seeking agent - retrieves data from sources."""

import json
from typing import Any

from ..core.config import Config
from ..core.logger import format_code, format_result, get_logger
from ..data.registry import DataRegistry
from ..llm import LLMClient
from ..tools.registry import ToolRegistry
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
        llm_client: LLMClient,
        tool_registry: ToolRegistry,
        data_registry: DataRegistry,
    ) -> None:
        super().__init__(config, llm_client)
        self.tool_registry = tool_registry
        self.data_registry = data_registry
        self._logger = get_logger("InfoSeeker")
        self._system_prompt = """You are an information seeking agent. Write Python code to extract the needed information from datasets.

You will be provided with detailed schema information about available datasets including column names, types, units, and value ranges. Use this information to write accurate queries.

You have access to a pandas DataFrame called `df`. Write code that computes the answer and stores it in a variable called `result`.

IMPORTANT:
- Use exact column names from the schema (e.g., 'heart_rate' not 'hr')
- Consider column units when reporting results (e.g., bpm, ms, steps)
- Always compute aggregated results (mean, sum, count, etc.), never return raw data
- Store your final answer in the `result` variable
- Keep results small and focused
- Available: df (pandas DataFrame), pd (pandas), np (numpy)

Examples:
- Average: result = df['heart_rate'].mean()
- Count: result = len(df)
- Sum: result = df['steps'].sum()
- Group stats: result = df.groupby('day')['steps'].mean().to_dict()
- Filtered count: result = len(df[df['value'] > 100])
- Multiple stats: result = {'mean': df['heart_rate'].mean(), 'max': df['heart_rate'].max()}
- Time conversion: result = pd.to_datetime(df['timestamp'], unit='s').dt.hour.value_counts().to_dict()

Respond with a JSON object:
{
    "source": "exact_dataset_name_from_schema",
    "query_type": "exec",
    "params": {"code": "result = df['exact_column_name'].mean()"}
}

Be precise and use exact column names from the provided schema."""

    def execute(
        self,
        info_request: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Seek information based on request.

        Args:
            info_request: Description of information needed.
            context: Additional context from sensemaker.

        Returns:
            Retrieved information and metadata.
        """
        return self.seek(info_request, context)

    def seek(
        self,
        info_request: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Seek information from available sources."""
        self._logger.debug(f"Seeking: {info_request}")

        # Get available sources info
        sources_info = self._get_sources_info()

        # Ask LLM what to query
        query_decision = self._decide_query(info_request, sources_info, context)

        if "error" in query_decision:
            self._logger.error(
                f"Failed to decide query: {query_decision.get('error', 'Unknown')}"
            )
            return {
                "request": info_request,
                "success": False,
                "error": query_decision.get("error", "Failed to decide query"),
                "results": [],
            }

        # Execute the query
        source_name = query_decision.get("source", "")
        query_type = query_decision.get("query_type", "")
        params = query_decision.get("params", {})

        # Log code execution
        if query_type == "exec" and "code" in params:
            self._logger.info(
                f"Executing on {source_name}:\n{format_code(params['code'])}"
            )
        else:
            self._logger.debug(f"Querying {source_name} with {query_type}")

        result = self._execute_query(source_name, query_type, params)

        # Log results
        if "error" in result:
            self._logger.error(f"Query failed: {result['error']}")
        else:
            result_value = result.get("result", result)
            self._logger.info(f"Result: {format_result(result_value)}")

        return {
            "request": info_request,
            "source": source_name,
            "query_type": query_type,
            "params": params,
            "results": result,
            "success": "error" not in result,
        }

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
    ) -> dict[str, Any]:
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
        response = self._call_llm(messages)
        return self._parse_response(response)

    def _execute_query(
        self, source_name: str, query_type: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute a query on a data source."""
        source = self.data_registry.get(source_name)
        if source is None:
            return {"error": f"Data source '{source_name}' not found"}

        try:
            result = source.query(query_type, **params)
            return result
        except Exception as e:
            return {"error": str(e)}

    def get_available_sources(self) -> list[dict[str, Any]]:
        """Get list of available data sources and tools."""
        sources = []
        sources.extend(self.data_registry.list_sources())
        sources.extend(self.tool_registry.list_tools())
        return sources
