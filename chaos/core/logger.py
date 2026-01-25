"""Logging infrastructure for CHAOS."""

import logging
import sys
from typing import Any


# ANSI color codes for terminal output
class Colors:
    """ANSI color codes for terminal formatting."""

    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    # Component colors
    ORCHESTRATOR = "\033[94m"  # Blue
    PLANNER = "\033[95m"  # Magenta
    SENSEMAKER = "\033[96m"  # Cyan
    INFOSEEKER = "\033[93m"  # Yellow
    VERIFIER = "\033[92m"  # Green
    MEMORY = "\033[90m"  # Gray

    # Level colors
    DEBUG = "\033[90m"  # Gray
    INFO = "\033[97m"  # White
    WARNING = "\033[93m"  # Yellow
    ERROR = "\033[91m"  # Red


# Map component names to colors
COMPONENT_COLORS = {
    "Orchestrator": Colors.ORCHESTRATOR,
    "Planner": Colors.PLANNER,
    "Sensemaker": Colors.SENSEMAKER,
    "InfoSeeker": Colors.INFOSEEKER,
    "Verifier": Colors.VERIFIER,
    "Memory": Colors.MEMORY,
}


class CHAOSFormatter(logging.Formatter):
    """Custom formatter for CHAOS logging with component tags and colors."""

    def __init__(self, use_colors: bool = True) -> None:
        super().__init__()
        self.use_colors = use_colors

    def format(self, record: logging.LogRecord) -> str:
        component = getattr(record, "component", "CHAOS")
        message = record.getMessage()

        if self.use_colors:
            color = COMPONENT_COLORS.get(component, Colors.INFO)
            level_color = getattr(Colors, record.levelname, Colors.INFO)

            # Format multi-line messages with proper indentation
            lines = message.split("\n")
            if len(lines) > 1:
                indent = " " * (len(component) + 3)
                formatted_lines = [lines[0]] + [indent + line for line in lines[1:]]
                message = "\n".join(formatted_lines)

            return f"{color}[{component}]{Colors.RESET} {message}"
        else:
            # Plain text formatting
            lines = message.split("\n")
            if len(lines) > 1:
                indent = " " * (len(component) + 3)
                formatted_lines = [lines[0]] + [indent + line for line in lines[1:]]
                message = "\n".join(formatted_lines)

            return f"[{component}] {message}"


class ComponentLogger(logging.LoggerAdapter):
    """Logger adapter that adds component context."""

    def __init__(self, logger: logging.Logger, component: str) -> None:
        super().__init__(logger, {"component": component})

    def process(
        self, msg: str, kwargs: dict[str, Any]
    ) -> tuple[str, dict[str, Any]]:
        kwargs["extra"] = kwargs.get("extra", {})
        kwargs["extra"]["component"] = self.extra["component"]
        return msg, kwargs


# Global logger instance
_logger: logging.Logger | None = None
_use_colors: bool = True


def setup_logging(level: str = "WARNING", use_colors: bool = True) -> None:
    """
    Configure CHAOS logging.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR).
        use_colors: Whether to use ANSI colors in output.
    """
    global _logger, _use_colors
    _use_colors = use_colors

    _logger = logging.getLogger("chaos")
    _logger.setLevel(getattr(logging, level.upper(), logging.WARNING))

    # Remove existing handlers
    _logger.handlers.clear()

    # Add console handler with custom formatter
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(CHAOSFormatter(use_colors=use_colors))
    _logger.addHandler(handler)

    # Prevent propagation to root logger
    _logger.propagate = False


def get_logger(component: str) -> ComponentLogger:
    """
    Get a component-specific logger.

    Args:
        component: Component name (e.g., 'Orchestrator', 'Planner').

    Returns:
        ComponentLogger instance with component context.
    """
    global _logger
    if _logger is None:
        setup_logging()
    return ComponentLogger(_logger, component)


def format_plan(plan: Any) -> str:
    """
    Format an execution plan for logging.

    Args:
        plan: Plan object or dictionary from the planner agent.

    Returns:
        Formatted multi-line string representation.
    """
    from ..types import Plan

    lines = ["Plan created:"]

    # Handle both Plan object and dict
    if isinstance(plan, Plan):
        if plan.query_understanding:
            lines.append(f"  Understanding: {plan.query_understanding}")

        if plan.data_sources:
            sources = ", ".join(plan.data_sources)
            lines.append(f"  Data Sources: {sources}")

        if plan.steps:
            lines.append("  Steps:")
            for step in plan.steps:
                source_str = f" (from {step.source})" if step.source else ""
                lines.append(f"    {step.step}. {step.action}{source_str}")

    else:
        # Fallback for dict (backward compatibility)
        if plan.get("query_understanding"):
            lines.append(f"  Understanding: {plan['query_understanding']}")

        if plan.get("data_sources"):
            sources = ", ".join(plan["data_sources"])
            lines.append(f"  Data Sources: {sources}")

        if plan.get("steps"):
            lines.append("  Steps:")
            for step in plan["steps"]:
                step_num = step.get("step", "?")
                action = step.get("action", "Unknown action")
                source = step.get("source", "")
                source_str = f" (from {source})" if source else ""
                lines.append(f"    {step_num}. {action}{source_str}")

    return "\n".join(lines)


def format_code(code: str) -> str:
    """
    Format Python code for logging.

    Args:
        code: Python code string.

    Returns:
        Formatted code block with delimiters.
    """
    lines = ["--- python code ---"]
    for line in code.strip().split("\n"):
        lines.append(f"  {line}")
    lines.append("--- end code ---")
    return "\n".join(lines)


def format_memory_state(memory_export: dict[str, Any]) -> str:
    """
    Format memory state for logging.

    Args:
        memory_export: Exported memory dict from Memory.export().

    Returns:
        Formatted memory state string.
    """
    entry_count = memory_export.get("entry_count", 0)
    if entry_count == 0:
        return "Memory: empty"

    lines = [f"Memory: {entry_count} entries"]

    entries = memory_export.get("entries", [])
    for i, entry in enumerate(entries[-5:], 1):  # Show last 5 entries
        content = entry.get("content", {})
        if isinstance(content, dict):
            # New format: {step, source, success, code, result/error}
            step = content.get("step", "?")
            source = content.get("source", "unknown")
            success = content.get("success", False)

            if "code" in content:
                # Truncate code for display
                code = content["code"]
                code_short = code.replace("\n", " ")[:60]
                if len(code) > 60:
                    code_short += "..."

                if success and "result" in content:
                    result_str = str(content["result"])
                    if len(result_str) > 80:
                        result_str = result_str[:80] + "..."
                    lines.append(f"  [{step}] {source}: `{code_short}` → {result_str}")
                elif "error" in content:
                    error_str = str(content["error"])[:80]
                    lines.append(f"  [{step}] {source}: `{code_short}` → ERROR: {error_str}")
                else:
                    lines.append(f"  [{step}] {source}: `{code_short}`")
            else:
                # Fallback for other entry types (e.g., error_recovery)
                entry_type = content.get("type", "info")
                lines.append(f"  [{i}] {entry_type}: {source}")
        else:
            content_str = str(content)
            if len(content_str) > 100:
                content_str = content_str[:100] + "..."
            lines.append(f"  [{i}] {content_str}")

    return "\n".join(lines)


def format_result(result: Any, max_length: int = 200) -> str:
    """
    Format a query result for logging.

    Args:
        result: Result value to format.
        max_length: Maximum string length before truncation.

    Returns:
        Formatted result string.
    """
    result_str = str(result)
    if len(result_str) > max_length:
        return result_str[:max_length] + "..."
    return result_str
