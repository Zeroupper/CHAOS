"""Base agent class for all CHAOS agents."""

from abc import ABC, abstractmethod
from typing import Any

from ..core.config import Config


class BaseAgent(ABC):
    """Abstract base class for all agents."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self._system_prompt: str = ""

    @property
    def system_prompt(self) -> str:
        """Get the agent's system prompt."""
        return self._system_prompt

    @system_prompt.setter
    def system_prompt(self, value: str) -> None:
        """Set the agent's system prompt."""
        self._system_prompt = value

    @abstractmethod
    def execute(self, *args: Any, **kwargs: Any) -> Any:
        """Execute the agent's main task."""
        ...

    def _call_llm(self, messages: list[dict[str, str]]) -> str:
        """Call the LLM with the given messages."""
        # TODO: Implement LLM calling based on config.llm settings
        raise NotImplementedError

    def _parse_response(self, response: str) -> dict[str, Any]:
        """Parse LLM response into structured format."""
        # TODO: Implement response parsing
        raise NotImplementedError
