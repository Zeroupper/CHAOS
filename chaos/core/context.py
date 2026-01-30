"""Context building utilities for the orchestrator."""

from typing import Any

from ..memory import Memory
from ..types import Plan


class ContextBuilder:
    """Builds context dictionaries for various orchestrator operations."""

    def __init__(self, memory: Memory) -> None:
        self.memory = memory

    def build_step_history(self, plan: Plan) -> list[dict]:
        """Build list of plan steps with their execution results."""
        step_executions = self.memory.get_step_executions()

        history = []
        for plan_step in plan.steps:
            entry = step_executions.get(plan_step.step)
            if entry:
                result = entry.result if entry.success else entry.error or "Not executed"
                history.append({
                    "step": plan_step.step,
                    "action": plan_step.action,
                    "source": plan_step.source,
                    "code": entry.code,
                    "result": result,
                    "success": entry.success,
                })
            else:
                history.append({
                    "step": plan_step.step,
                    "action": plan_step.action,
                    "source": plan_step.source,
                    "code": "",
                    "result": "Not executed",
                    "success": False,
                })
        return history

    def build_step_context_for_info_seeker(self, plan: Plan) -> dict[str, Any]:
        """
        Build context about previous step results for the InformationSeekingAgent.

        This allows user-added steps to reference previous results like
        "subtract 10 from step 3 result".
        """
        step_executions = self.memory.get_step_executions()
        step_results = {}

        for step_num, entry in step_executions.items():
            if entry.success:
                step_results[f"step_{step_num}"] = {
                    "result": entry.result,
                    "action": None,  # Will fill from plan
                }

        # Add action descriptions from plan
        for plan_step in plan.steps:
            key = f"step_{plan_step.step}"
            if key in step_results:
                step_results[key]["action"] = plan_step.action

        return {
            "previous_step_results": step_results,
            "instructions": (
                "The user is adding a new step that may reference previous results. "
                "Use the values from previous_step_results when the user says things like "
                "'step 3 result' or 'the result'. For example, if step_3 result is 156.0, "
                "and user says 'subtract 10 from step 3 result', compute: result = 156.0 - 10"
            ),
        }

    def build_replan_context(
        self, step_history: list[dict], suggested_fix: str | None
    ) -> str:
        """
        Build context string for replanning with learnings from previous attempt.

        Args:
            step_history: List of step execution results.
            suggested_fix: Optional user-provided guidance.

        Returns:
            Formatted context string to append to available sources.
        """
        context_parts = [
            "\n## LEARNINGS FROM PREVIOUS ATTEMPT",
            "A previous plan was executed but did not fully answer the question.",
            "Use these learnings to inform a COMPLETELY DIFFERENT approach.\n",
        ]

        # Extract learnings (facts discovered), not "results to reuse"
        learnings = []
        for step in step_history:
            action = step.get("action", "Unknown")
            result = step.get("result", "No result")
            success = step.get("success", False)

            if success:
                learnings.append(f"- {action} -> Result: {result[:200]}")
            else:
                learnings.append(f"- {action} -> FAILED: {result[:200]}")

        context_parts.append("### What was attempted and discovered:")
        context_parts.extend(learnings)
        context_parts.append("")

        if suggested_fix and suggested_fix.strip():
            context_parts.append("### USER FEEDBACK (important):")
            context_parts.append(suggested_fix)
            context_parts.append("")

        context_parts.append(
            "IMPORTANT: Create a FRESH plan. Do NOT simply repeat the previous "
            "approach with minor variations. Consider completely different methods "
            "or data sources if the previous approach was fundamentally flawed."
        )

        return "\n".join(context_parts)
