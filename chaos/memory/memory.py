"""Memory management for the sensemaking process."""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

# Default maximum characters per memory entry
DEFAULT_ENTRY_SIZE_LIMIT = 2000


@dataclass
class MemoryEntry:
    """Single entry in working memory."""

    content: Any
    timestamp: datetime = field(default_factory=datetime.now)
    truncated: bool = False


class Memory:
    """
    Working memory for the sensemaking process.

    Stores information gathered during the sensemaking loop
    and provides methods for retrieval and summarization.
    """

    def __init__(self, entry_size_limit: int = DEFAULT_ENTRY_SIZE_LIMIT) -> None:
        self._entries: list[MemoryEntry] = []
        self._summary: str = ""
        self._entry_size_limit = entry_size_limit

    def update(self, info: dict[str, Any]) -> None:
        """
        Add new information to memory.

        Args:
            info: Information dict with 'content'.
        """
        content = info.get("content")
        truncated = False

        # Apply size limit if content is a string
        if isinstance(content, str) and len(content) > self._entry_size_limit:
            logger.warning(
                f"Memory entry truncated from {len(content)} to {self._entry_size_limit} chars"
            )
            content = content[: self._entry_size_limit] + "...[truncated]"
            truncated = True
        elif not isinstance(content, str):
            # Convert to string and check size
            content_str = str(content)
            if len(content_str) > self._entry_size_limit:
                logger.warning(
                    f"Memory entry truncated from {len(content_str)} to {self._entry_size_limit} chars"
                )
                content = content_str[: self._entry_size_limit] + "...[truncated]"
                truncated = True

        entry = MemoryEntry(content=content, truncated=truncated)
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

    def export(self) -> dict[str, Any]:
        """
        Export memory contents for final result.

        Returns:
            Dictionary with memory summary and entries.
        """
        return {
            "summary": self._summary,
            "entry_count": len(self._entries),
            "entries": [
                {
                    "content": entry.content,
                    "timestamp": entry.timestamp.isoformat(),
                    "truncated": entry.truncated,
                }
                for entry in self._entries
            ],
        }
