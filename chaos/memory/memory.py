"""Memory management for the sensemaking process."""

from dataclasses import dataclass
from typing import Any


@dataclass
class MemoryEntry:
    """Single entry in working memory storing code execution results."""

    code: str
    result: Any
    success: bool = True
    error: str | None = None
    step: int | None = None


class Memory:
    """
    Working memory for the sensemaking process.

    Stores code executions and their results during the sensemaking loop.
    """

    def __init__(self) -> None:
        self._entries: list[MemoryEntry] = []

    def add(
        self,
        code: str,
        result: Any,
        success: bool = True,
        error: str | None = None,
        step: int | None = None,
    ) -> None:
        """
        Add a code execution result to memory.

        Args:
            code: The code that was executed.
            result: The execution result.
            success: Whether execution succeeded.
            error: Error message if failed.
            step: Optional step number from the plan.
        """
        entry = MemoryEntry(
            code=code,
            result=result,
            success=success,
            error=error,
            step=step,
        )
        self._entries.append(entry)

    def get_entries(self, limit: int | None = None) -> list[MemoryEntry]:
        """
        Get memory entries.

        Args:
            limit: Maximum number of entries to return (most recent).

        Returns:
            List of memory entries.
        """
        if limit:
            return self._entries[-limit:]
        return self._entries

    def clear(self) -> None:
        """Clear all memory entries."""
        self._entries = []

    def get_context_for_llm(self, max_entries: int = 10) -> str:
        """
        Format memory contents for inclusion in LLM prompt.

        Args:
            max_entries: Maximum entries to include.

        Returns:
            Formatted string for LLM context.
        """
        if not self._entries:
            return "No code executed yet."

        recent = self._entries[-max_entries:]
        lines = ["Previous executions:"]
        for entry in recent:
            step_info = f"Step {entry.step}: " if entry.step is not None else ""
            lines.append(f"\n{step_info} Code:\n```\n{entry.code}\n```")
            if entry.success:
                lines.append(f"Result: {entry.result}")
            else:
                lines.append(f"Error: {entry.error}")
        return "\n".join(lines)

    def export(self) -> dict[str, Any]:
        """
        Export memory contents for final result.

        Returns:
            Dictionary with entry count and entries.
        """
        return {
            "entries": [
                {
                    "code": entry.code,
                    "result": entry.result,
                    "success": entry.success,
                    "error": entry.error,
                    "step": entry.step,
                }
                for entry in self._entries
            ],
        }

    def get_step_executions(self) -> dict[int, MemoryEntry]:
        """
        Get execution entries grouped by step number.

        Returns:
            Dictionary mapping step numbers to their MemoryEntry.
        """
        executions: dict[int, MemoryEntry] = {}
        for entry in self._entries:
            if entry.step is not None:
                executions[entry.step] = entry
        return executions
