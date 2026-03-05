"""Information seeking agent - retrieves data from sources."""

import json
from typing import Any

from ..core.code_executor import CodeExecutor
from ..core.config import Config
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
        self._system_prompt = """Write Python code to query datasets. Store output in `result`.

Available variables: all datasets by name, `pd`, `np`, and `step_N_result` (only if listed as available).
Do NOT assign to `step_N_result`. Use exact column names."""

    def _build_prompt(self, info_request: str, context: dict[str, Any] | None = None) -> str:
        """Build the user prompt for the LLM call."""
        context_str = ""
        if context:
            context_str = f"\nAdditional context:\n{json.dumps(context, indent=2)}"

        return f"""{info_request}

{self.data_registry.get_sources_prompt()}
{self._executor.describe_step_results()}
{context_str}"""

    def seek(
        self,
        info_request: str,
        context: dict[str, Any] | None = None,
    ) -> InfoSeekerResult:
        """Seek information from available sources."""
        # Ask LLM what code to execute
        prompt = self._build_prompt(info_request, context)
        try:
            query_decision = self._call_llm([{"role": "user", "content": prompt}], QueryDecision)
        except Exception as e:
            return InfoSeekerResult(
                request=info_request,
                source="unknown",
                query_type="exec",
                params={},
                results=f"LLM failed to generate query: {e}",
                success=False,
            )

        # Execute the query
        code = query_decision.params.code

        step_num = self.state.current_step if self.state else None
        exec_result = self._executor.execute(code, step_num=step_num)

        params_dict = {"code": code}

        if exec_result.error:
            return InfoSeekerResult(
                request=info_request,
                source=query_decision.source,
                query_type=query_decision.query_type,
                params=params_dict,
                results=exec_result.error,
                success=False,
            )
        else:
            return InfoSeekerResult(
                request=info_request,
                source=query_decision.source,
                query_type=query_decision.query_type,
                params=params_dict,
                results=exec_result.result or "",
                success=True,
            )
