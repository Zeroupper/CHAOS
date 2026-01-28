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


def approve_correction(
    step: int,
    issue: str,
    proposed_fix: str,
) -> tuple[str, str | None]:
    """
    Prompt user to approve/modify a data quality correction.

    Args:
        step: The affected step number.
        issue: Description of the data quality issue.
        proposed_fix: The proposed correction query.

    Returns:
        Tuple of (decision, modified_request).
        decision: "approve", "modify", or "skip"
        modified_request: User's modified request if decision is "modify", else None
    """
    from rich.console import Console
    from rich.panel import Panel

    console = Console()

    # Display the correction proposal
    content = (
        f"[bold]Issue:[/bold] {issue}\n\n"
        f"[bold]Proposed fix:[/bold] {proposed_fix}"
    )
    console.print(Panel(content, title=f"Step {step} - Data Quality Issue", border_style="yellow"))

    decision = questionary.select(
        "How would you like to handle this?",
        choices=[
            Choice("Approve proposed correction", value="approve"),
            Choice("Modify the correction", value="modify"),
            Choice("Skip (continue without fixing)", value="skip"),
        ],
        style=custom_style,
    ).ask()

    if decision is None:
        return ("skip", None)

    modified_request = None
    if decision == "modify":
        modified_request = questionary.text(
            "Enter your corrected request:",
            default=proposed_fix,
            style=custom_style,
        ).ask()
        if modified_request is None:
            return ("skip", None)

    return (decision, modified_request)


def prompt_export_run(default_path: str) -> str | None:
    """
    Prompt user to export the run to a markdown file.

    Args:
        default_path: Default path for the export file.

    Returns:
        Path to export to, or None to skip export.
    """
    should_export = questionary.confirm(
        "Export this run to a markdown file?",
        default=False,
        style=custom_style,
    ).ask()

    if not should_export:
        return None

    path = questionary.text(
        "Export path:",
        default=default_path,
        style=custom_style,
    ).ask()

    return path
