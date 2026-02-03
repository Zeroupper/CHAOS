"""Logging for CHAOS using loguru."""

import sys

from loguru import logger


def setup_logging(level: str = "WARNING") -> None:
    """Configure logging with specified level."""
    logger.remove()
    logger.add(
        sys.stderr,
        format="<level>[{extra[component]}]</level> {message}",
        level=level.upper(),
        colorize=True,
    )


def get_logger(component: str):
    """Get logger for a component (e.g., 'Orchestrator', 'InformationSeeker')."""
    return logger.bind(component=component)


def format_code(code: str) -> str:
    """Format code block for logging."""
    indented = "\n".join(f"  {line}" for line in code.strip().split("\n"))
    return f"--- python code ---\n{indented}\n--- end code ---"


def format_result(result, max_length: int = 200) -> str:
    """Format result, truncating if too long."""
    s = str(result)
    return s if len(s) <= max_length else s[:max_length] + "..."
