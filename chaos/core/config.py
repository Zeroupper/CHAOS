"""Configuration management for CHAOS."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class LLMConfig:
    """LLM provider configuration."""

    provider: str = "openrouter"
    model: str = "anthropic/claude-sonnet-4"
    api_key: str | None = None

@dataclass
class Config:
    """Main configuration for CHAOS."""

    llm: LLMConfig = field(default_factory=LLMConfig)
    max_iterations: int = 5
    datasets_dir: Path = field(default_factory=lambda: Path("datasets"))
    verbose: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Config":
        """Create config from dictionary."""
        llm_data = data.pop("llm", {})
        llm_config = LLMConfig(**llm_data)
        return cls(llm=llm_config, **data)

    @classmethod
    def from_file(cls, path: Path) -> "Config":
        """Load config from YAML/JSON file."""
        # TODO: Implement file loading
        raise NotImplementedError
