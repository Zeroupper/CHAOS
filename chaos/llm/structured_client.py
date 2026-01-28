"""Instructor-based LLM client for structured outputs."""

from typing import TypeVar

import instructor
from openai import OpenAI
from pydantic import BaseModel

from ..core.config import LLMConfig

T = TypeVar("T", bound=BaseModel)


class StructuredLLMClient:
    """
    LLM client that returns validated Pydantic models.

    Works with ANY OpenRouter model (GPT-4o, DeepSeek, Kimi K2, Claude, etc.)
    via the OpenAI-compatible API format.
    """

    OPENROUTER_URL = "https://openrouter.ai/api/v1"

    def __init__(self, config: LLMConfig, max_retries: int = 3) -> None:
        self.config = config
        self.max_retries = max_retries
        # LLMConfig (pydantic-settings) auto-loads OPENROUTER_API_KEY from environment
        self._api_key = config.api_key

        if not self._api_key:
            raise ValueError(
                "OpenRouter API key not found. Set OPENROUTER_API_KEY environment "
                "variable or pass api_key in LLMConfig."
            )

        # OpenAI client pointing to OpenRouter - works with ALL OpenRouter models
        self._openai_client = OpenAI(
            base_url=self.OPENROUTER_URL,
            api_key=self._api_key,
            default_headers={
                "HTTP-Referer": "https://github.com/chaos-agents",
                "X-Title": "CHAOS Multi-Agent System",
            },
        )

        # Wrap with Instructor for structured outputs
        self._client = instructor.from_openai(
            self._openai_client,
            mode=instructor.Mode.JSON,
        )

    def chat(
        self,
        messages: list[dict[str, str]],
        response_model: type[T],
        system: str | None = None,
    ) -> T:
        """
        Get a validated structured response.

        Args:
            messages: List of message dicts with 'role' and 'content' keys.
            response_model: Pydantic model class for response validation.
            system: Optional system prompt to prepend.

        Returns:
            Validated Pydantic model instance.
        """
        if system:
            messages = [{"role": "system", "content": system}] + messages

        return self._client.chat.completions.create(
            model=self.config.model,  # e.g., "openai/gpt-4o", "deepseek/deepseek-chat"
            messages=messages,
            response_model=response_model,
            max_retries=self.max_retries,
        )
