"""Questionary-based interactive prompts for CHAOS."""

import questionary
from questionary import Choice, Style

from ..types import Plan

# Custom style similar to Claude Code
custom_style = Style(
    [
        ("qmark", "fg:cyan bold"),
        ("question", "bold"),
        ("answer", "fg:green"),
        ("pointer", "fg:cyan bold"),
        ("highlighted", "fg:cyan bold"),
        ("selected", "fg:green"),
    ]
)


def approve_plan(plan: Plan) -> str | None:
    """Prompt user to approve, modify, or reject the plan."""
    return questionary.select(
        "How would you like to proceed with this plan?",
        choices=[
            Choice("Approve and execute", value="approve"),
            Choice("Modify plan steps", value="modify"),
            Choice("Reject", value="reject"),
        ],
        style=custom_style,
    ).ask()


def modify_plan_step(step_num: int, current_action: str) -> str | None:
    """Allow user to modify a plan step."""
    return questionary.text(
        f"Modify step {step_num} (Enter to keep current):",
        default=current_action,
        style=custom_style,
    ).ask()


def final_review(recommendation: str, has_steps: bool = True) -> str | None:
    """Prompt user for final action based on verification."""
    choices = [
        Choice("Accept answer", value="accept"),
        Choice("Reject", value="reject"),
    ]
    if has_steps:
        choices.insert(1, Choice("Revise (fix a step)", value="revise"))
        choices.insert(2, Choice("Replan (fresh start with learnings)", value="replan"))

    return questionary.select(
        "Final review - what would you like to do?",
        choices=choices,
        style=custom_style,
    ).ask()


def select_step_to_revise(steps: list[dict]) -> int | str | None:
    """Let user select which step to revise or add a new step."""
    choices = [Choice("➕ Add new step", value="add_new")]
    for s in steps:
        action = s["action"][:70]
        status = "✓" if s.get("success") else "✗"
        choices.append(
            Choice(
                f"Step {s['step']} [{status}]: {action}",
                value=s["step"],
            )
        )
    choices.append(Choice("Cancel", value=None))

    return questionary.select(
        "Select an action:",
        choices=choices,
        style=custom_style,
    ).ask()


def get_new_step_action() -> str | None:
    """Get user's action for a new step."""
    return questionary.text(
        "Enter the action for the new step:",
        style=custom_style,
    ).ask()


def get_revised_request(original: str) -> str | None:
    """Get user's revised request for a step."""
    return questionary.text(
        "Enter your corrected request for this step:",
        default=original,
        style=custom_style,
    ).ask()


def get_replan_suggestion() -> str | None:
    """Get user's suggested fix to guide the planner in creating a new plan."""
    return questionary.text(
        "Enter a suggested fix to guide the new plan (leave empty to auto-replan):",
        style=custom_style,
    ).ask()
