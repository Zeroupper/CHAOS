"""Base agent class for all CHAOS agents."""

from abc import ABC, abstractmethod
from typing import Any, TypeVar

from pydantic import BaseModel

from ..core.config import Config
from ..llm.structured_client import StructuredLLMClient

T = TypeVar("T", bound=BaseModel)


class BaseAgent(ABC):
    """Abstract base class for all agents."""

    def __init__(self, config: Config, llm_client: StructuredLLMClient) -> None:
        self.config = config
        self.llm_client = llm_client
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

    def _call_llm(
        self,
        messages: list[dict[str, str]],
        response_model: type[T],
    ) -> T:
        """
        Call the LLM and get a validated Pydantic model response.

        Args:
            messages: List of message dicts with 'role' and 'content'.
            response_model: Pydantic model class for response validation.

        Returns:
            Validated Pydantic model instance.
        """
        return self.llm_client.chat(
            messages,
            response_model,
            system=self._system_prompt,
        )
