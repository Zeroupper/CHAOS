"""Memory management for the sensemaking process."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class MemoryEntry:
    """Single entry in working memory."""

    content: Any
    source: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)


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
            info: Information dict with 'content', 'source', and optional 'metadata'.
        """
        entry = MemoryEntry(
            content=info.get("content"),
            source=info.get("source", "unknown"),
            metadata=info.get("metadata", {}),
        )
        self._entries.append(entry)
        self._update_summary()

    def get_entries(
        self,
        source: str | None = None,
        limit: int | None = None,
    ) -> list[MemoryEntry]:
        """
        Get memory entries, optionally filtered by source.

        Args:
            source: Filter by source name.
            limit: Maximum number of entries to return.

        Returns:
            List of memory entries.
        """
        entries = self._entries
        if source:
            entries = [e for e in entries if e.source == source]
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

    def export(self) -> dict[str, Any]:
        """Export memory state for persistence or inspection."""
        return {
            "entries": [
                {
                    "content": e.content,
                    "source": e.source,
                    "timestamp": e.timestamp.isoformat(),
                    "metadata": e.metadata,
                }
                for e in self._entries
            ],
            "summary": self._summary,
        }

    def _update_summary(self) -> None:
        """Update the memory summary after new entries."""
        # TODO: Implement summarization (possibly using LLM)
        sources = set(e.source for e in self._entries)
        self._summary = f"Memory contains {len(self._entries)} entries from: {', '.join(sources)}"

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
            lines.append(f"\n{i}. From {entry.source}:")
            lines.append(f"   {entry.content}")
        return "\n".join(lines)
