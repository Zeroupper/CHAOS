"""Memory management for the sensemaking process."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class MemoryEntry:
    """Single entry in working memory."""

    content: Any
    timestamp: datetime = field(default_factory=datetime.now)


class Memory:
    """
    Working memory for the sensemaking process.

    Stores information gathered during the sensemaking loop
    and provides methods for retrieval and summarization.
    """

    def __init__(self) -> None:
        self._entries: list[MemoryEntry] = []
        self._summary: str = ""

    def update(self, info: dict[str, Any]) -> None:
        """
        Add new information to memory.

        Args:
            info: Information dict with 'content'.
        """
        entry = MemoryEntry(content=info.get("content"))
        self._entries.append(entry)
        self._update_summary()

    def get_entries(self, limit: int | None = None) -> list[MemoryEntry]:
        """
        Get memory entries.

        Args:
            limit: Maximum number of entries to return.

        Returns:
            List of memory entries.
        """
        entries = self._entries
        if limit:
            entries = entries[-limit:]
        return entries

    def get_summary(self) -> str:
        """Get current summary of memory contents."""
        return self._summary

    def clear(self) -> None:
        """Clear all memory entries."""
        self._entries = []
        self._summary = ""

    def _update_summary(self) -> None:
        """Update the memory summary after new entries."""
        # TODO: Implement summarization (possibly using LLM)
        self._summary = f"Memory contains {len(self._entries)} entries."

    def get_context_for_llm(self, max_entries: int = 10) -> str:
        """
        Format memory contents for inclusion in LLM prompt.

        Args:
            max_entries: Maximum entries to include.

        Returns:
            Formatted string for LLM context.
        """
        if not self._entries:
            return "No information gathered yet."

        recent = self._entries[-max_entries:]
        lines = ["Information gathered so far:"]
        for i, entry in enumerate(recent, 1):
            lines.append(f"\n{i}. {entry.content}")
        return "\n".join(lines)
