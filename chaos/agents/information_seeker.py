"""Information seeking agent - retrieves data from sources."""

from typing import Any

from ..core.code_executor import CodeExecutor
from ..core.config import Config
from ..core.context import build_query_prompt
from ..core.logger import format_code, format_result
from ..core.state import ExecutionState
from ..data.registry import DataRegistry
from ..llm.structured_client import StructuredLLMClient
from ..types import InfoSeekerResult, QueryDecision
from .base import BaseAgent


class InformationSeekingAgent(BaseAgent):
    """
    Seeks information from data sources.

    Responsibilities:
    - Interpret information requests from sensemaker
    - Query appropriate data sources
    - Return structured results
    """

    def __init__(
        self,
        config: Config,
        llm_client: StructuredLLMClient,
        data_registry: DataRegistry,
        executor: CodeExecutor,
        state: ExecutionState | None = None,
    ) -> None:
        super().__init__(config, llm_client)
        self.data_registry = data_registry
        self._executor = executor
        self.state = state
        self._system_prompt = """You are an information seeking agent. Write Python code to query datasets.

NAMESPACE: All datasets pre-loaded by name, `pd`, `np`, and previous step outputs (`step_N_result` — only if listed as available below). Do NOT assign to `step_N_result` — just set `result`.

RULES:
1. Store output in `result`.
2. Use exact column names from the schema.
3. Match dtypes: if a column is int64, use int operations.

Respond with: {"source": "dataset_name", "query_type": "exec", "params": {"code": "result = ..."}}"""

    def seek(
        self,
        info_request: str,
        context: dict[str, Any] | None = None,
    ) -> InfoSeekerResult:
        """Seek information from available sources."""
        self._logger.debug(f"Seeking: {info_request}")

        # Ask LLM what code to execute
        prompt = build_query_prompt(
            info_request,
            self.data_registry.get_sources_prompt(),
            self._executor.describe_step_results(),
            context,
        )
        try:
            query_decision = self._call_llm([{"role": "user", "content": prompt}], QueryDecision)
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
            self._logger.info(f"Executing:\n{format_code(params['code'])}")
        else:
            self._logger.debug(f"Querying with {query_type}")

        code = params.get("code", "")
        if not code:
            exec_result_error = "No code provided"
            self._logger.error(f"Query failed: {exec_result_error}")
            return InfoSeekerResult(
                request=info_request,
                source=source_name,
                query_type=query_type,
                params=params,
                results=exec_result_error,
                success=False,
            )

        step_num = self.state.current_step if self.state else None
        exec_result = self._executor.execute(code, step_num=step_num)

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

