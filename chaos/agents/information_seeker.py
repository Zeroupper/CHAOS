"""Information seeking agent - retrieves data from sources."""

from typing import Any

from ..core.config import Config
from ..data.registry import DataRegistry
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
        tool_registry: ToolRegistry,
        data_registry: DataRegistry,
    ) -> None:
        super().__init__(config)
        self.tool_registry = tool_registry
        self.data_registry = data_registry
        self._system_prompt = """You are an information seeking agent. Your task is to:
        1. Understand what information the sensemaker needs
        2. Identify the best data sources or tools to use
        3. Formulate and execute queries
        4. Return structured results

        Available data sources and tools will be provided to you.
        """

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
        # Determine which sources/tools to use
        sources = self._identify_sources(info_request)

        # Execute queries
        results = []
        for source in sources:
            result = self._query_source(source, info_request, context)
            results.append(result)

        return {
            "request": info_request,
            "sources_used": sources,
            "results": results,
            "success": len(results) > 0,
        }

    def _identify_sources(self, info_request: str) -> list[str]:
        """Identify which data sources or tools to use."""
        # TODO: Implement source identification logic
        return []

    def _query_source(
        self,
        source: str,
        info_request: str,
        context: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Query a specific data source or tool."""
        # TODO: Implement query execution
        return {"source": source, "data": None, "error": None}

    def get_available_sources(self) -> list[dict[str, Any]]:
        """Get list of available data sources and tools."""
        sources = []
        sources.extend(self.data_registry.list_sources())
        sources.extend(self.tool_registry.list_tools())
        return sources
