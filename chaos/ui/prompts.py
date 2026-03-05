"""Questionary-based interactive prompts for CHAOS."""

import questionary
from questionary import Choice, Style

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


def approve_plan() -> str | None:
    """Prompt user to approve, modify, or reject the plan."""
    return questionary.select(
        "How would you like to proceed with this plan?",
        choices=[
            Choice("Approve and execute", value="approve"),
            Choice("Modify plan", value="modify"),
            Choice("Reject", value="reject"),
        ],
        style=custom_style,
    ).ask()


def get_plan_feedback() -> str | None:
    """Get user feedback on what to change in the plan."""
    return questionary.text(
        "What would you like to change about the plan?",
        style=custom_style,
    ).ask()


def final_review() -> str | None:
    """Prompt user for final action based on verification."""
    return questionary.select(
        "Final review - what would you like to do?",
        choices=[
            Choice("Accept answer", value="accept"),
            Choice("Modify plan", value="modify"),
            Choice("Explain answer", value="explain"),
            Choice("Reject", value="reject"),
        ],
        style=custom_style,
    ).ask()


def get_explain_question() -> str | None:
    """Prompt the user for a question about the answer."""
    return questionary.text(
        "What would you like to know about this answer? (empty to go back)",
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
