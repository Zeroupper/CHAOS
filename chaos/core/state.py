"""Unified execution state management for CHAOS."""

from dataclasses import dataclass
from typing import Any

from ..types import Plan, StepState
from .logger import truncate_for_llm


@dataclass
class MemoryEntry:
    """Single entry storing code execution results."""

    code: str
    result: Any
    success: bool = True
    error: str | None = None
    step: int | None = None
    is_internal_context: bool = False


class ExecutionState:
    """
    Unified state tracking for plan execution.

    Consolidates step states and memory entries into a single source of truth.
    Step result strings are stored for LLM display only — raw Python objects
    are kept in CodeExecutor for step-to-step data passing.
    """

    def __init__(self) -> None:
        self._current_step: int = 0
        self._step_states: dict[int, StepState] = {}
        self._entries: list[MemoryEntry] = []

    @property
    def current_step(self) -> int:
        """Get current step number."""
        return self._current_step

    @current_step.setter
    def current_step(self, value: int) -> None:
        """Set current step number."""
        self._current_step = value

    @property
    def step_states(self) -> dict[int, StepState]:
        """Get all step states."""
        return self._step_states

    def record_result(
        self,
        step: int,
        code: str,
        result: str | None,
        success: bool,
        error: str | None = None,
    ) -> None:
        """
        Record a step execution result.

        Updates both step state and memory entries.

        Args:
            step: Step number.
            code: Code that was executed.
            result: Serialized result string (for display/LLM only).
            success: Whether execution succeeded.
            error: Error message if failed.
        """
        # Add memory entry
        self._entries.append(
            MemoryEntry(
                code=code,
                result=result if success else None,
                success=success,
                error=error if not success else None,
                step=step,
            )
        )

        # Update step state
        if success:
            self._step_states[step] = StepState.from_result(step, "completed", result)
        else:
            self._step_states[step] = StepState.from_result(
                step, "failed", failure_reason=error
            )

    def get_step_state(self, step: int) -> StepState | None:
        """Get state for a specific step."""
        return self._step_states.get(step)

    def set_step_state(self, step: int, state: StepState) -> None:
        """Set state for a specific step."""
        self._step_states[step] = state

    def reset_step(self, step: int) -> None:
        """Reset a specific step to pending state, clearing old memory entries."""
        if step in self._step_states:
            del self._step_states[step]
        self._entries = [e for e in self._entries if e.step != step]
        if step <= self._current_step:
            self._current_step = step - 1

    def reset(self) -> None:
        """Reset all state for a new query."""
        self._current_step = 0
        self._step_states = {}
        self._entries = []

    def record_context(self, step: int, message: str) -> None:
        """Record an internal context entry (e.g. human-agent correction interaction)."""
        self._entries.append(
            MemoryEntry(code="", result=message, is_internal_context=True, step=step)
        )

    def get_entries(self, limit: int | None = None) -> list[MemoryEntry]:
        """Get memory entries, optionally limited to most recent."""
        if limit:
            return self._entries[-limit:]
        return self._entries

    def format_step_states(self, plan: Plan) -> str:
        """Format execution status of each plan step for LLM prompts."""
        if not plan.steps:
            return "No steps defined."

        lines = []
        for plan_step in plan.steps:
            step_num = plan_step.step
            state = self._step_states.get(step_num)

            if not state:
                lines.append(f"  Step {step_num}: [pending] - Not yet executed")
            elif state.status == "completed":
                result_str = truncate_for_llm(state.result or "", 100)
                var_name = f"step_{step_num}_result"
                if state.user_accepted:
                    lines.append(f"  Step {step_num}: [completed] {var_name}={result_str} (USER ACCEPTED - do not propose corrections)")
                else:
                    lines.append(f"  Step {step_num}: [completed] {var_name}={result_str}")
            elif state.status == "failed":
                lines.append(
                    f"  Step {step_num}: [failed] "
                    f"reason={state.failure_reason}"
                )

        return "\n".join(lines)

    def get_context_for_llm(self, max_entries: int = 20, max_result_chars: int = 200) -> str:
        """Format state for inclusion in LLM prompt.

        Results are truncated to ``max_result_chars`` to stay within
        context limits — the full values are passed separately via
        step_N_result variables.
        """
        if not self._entries:
            return "No code executed yet."

        recent = self._entries[-max_entries:]
        lines = ["Previous executions:"]
        for entry in recent:
            step_info = f"Step {entry.step}: " if entry.step is not None else ""
            lines.append(f"\n{step_info} Code:\n```\n{entry.code}\n```")
            if entry.success:
                result_str = str(entry.result) if entry.result is not None else ""
                result_str = truncate_for_llm(result_str, max_result_chars)
                lines.append(f"Result: {result_str}")
            else:
                lines.append(f"Error: {entry.error}")
        return "\n".join(lines)

    def export(self) -> dict:
        """Export state for final result."""
        return {
            "entries": [
                {
                    "code": entry.code,
                    "result": entry.result,
                    "success": entry.success,
                    "error": entry.error,
                    "step": entry.step,
                    "is_internal_context": entry.is_internal_context,
                }
                for entry in self._entries
            ],
        }
