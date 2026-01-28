"""Logging infrastructure for CHAOS using loguru."""

import sys
from typing import Any

from loguru import logger

# Component colors for loguru format
COMPONENT_COLORS = {
    "Orchestrator": "blue",
    "Planner": "magenta",
    "Sensemaker": "cyan",
    "InfoSeeker": "yellow",
    "Verifier": "green",
    "Memory": "white",
}

# Global state
_configured = False


def setup_logging(level: str = "WARNING", use_colors: bool = True) -> None:
    """
    Configure CHAOS logging with loguru.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR).
        use_colors: Whether to use ANSI colors in output.
    """
    global _configured

    # Remove default handler
    logger.remove()

    # Build format string
    if use_colors:
        fmt = "<level>[{extra[component]}]</level> {message}"
    else:
        fmt = "[{extra[component]}] {message}"

    logger.add(
        sys.stderr,
        format=fmt,
        level=level.upper(),
        colorize=use_colors,
    )
    _configured = True


def get_logger(component: str) -> Any:
    """
    Get a component-specific logger.

    Args:
        component: Component name (e.g., 'Orchestrator', 'Planner').

    Returns:
        Logger instance bound to component.
    """
    global _configured
    if not _configured:
        setup_logging()
    return logger.bind(component=component)


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
            step = content.get("step", "?")
            source = content.get("source", "unknown")
            success = content.get("success", False)

            if "code" in content:
                code = content["code"]
                code_short = code.replace("\n", " ")[:60]
                if len(code) > 60:
                    code_short += "..."

                if success and "result" in content:
                    result_str = str(content["result"])
                    if len(result_str) > 80:
                        result_str = result_str[:80] + "..."
                    lines.append(f"  [{step}] {source}: `{code_short}` -> {result_str}")
                elif "error" in content:
                    error_str = str(content["error"])[:80]
                    lines.append(f"  [{step}] {source}: `{code_short}` -> ERROR: {error_str}")
                else:
                    lines.append(f"  [{step}] {source}: `{code_short}`")
            else:
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
