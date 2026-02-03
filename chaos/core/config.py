"""Configuration management for CHAOS."""

from dataclasses import dataclass
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMConfig(BaseSettings):
    """LLM provider configuration with automatic env loading."""

    model_config = SettingsConfigDict(env_prefix="OPENROUTER_")

    provider: str = "openrouter"
    model: str = "openai/gpt-oss-safeguard-20b"
    api_key: str | None = None
    max_tokens: int = 4096  # Safe default that works with most API key limits


@dataclass
class LogConfig:
    """Logging configuration."""

    level: str = "WARNING"


@dataclass
class Config:
    """Main configuration for CHAOS."""

    llm: LLMConfig
    log: LogConfig
    max_step_attempts: int = 5  # Max different approaches for a step
    datasets_dir: Path = Path("datasets")
