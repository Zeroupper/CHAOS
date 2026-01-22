"""Configuration management for CHAOS."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class LLMConfig:
    """LLM provider configuration."""

    provider: str = "openrouter"
    model: str = "openai/chatgpt-4o-latest"
    api_key: str | None = None


@dataclass
class LogConfig:
    """Logging configuration."""

    level: str = "WARNING"
    use_colors: bool = True


@dataclass
class Config:
    """Main configuration for CHAOS."""

    llm: LLMConfig = field(default_factory=LLMConfig)
    log: LogConfig = field(default_factory=LogConfig)
    max_iterations: int = 5
    datasets_dir: Path = field(default_factory=lambda: Path("datasets"))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Config":
        """Create config from dictionary."""
        llm_data = data.pop("llm", {})
        llm_config = LLMConfig(**llm_data)
        log_data = data.pop("log", {})
        log_config = LogConfig(**log_data)
        return cls(llm=llm_config, log=log_config, **data)

    @classmethod
    def from_file(cls, path: Path) -> "Config":
        """Load config from YAML/JSON file."""
        # TODO: Implement file loading
        raise NotImplementedError
