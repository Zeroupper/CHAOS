"""Rich-based display components for CHAOS."""

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from ..types import Plan, Verification

console = Console()


def display_plan(plan: Plan) -> None:
    """Display execution plan in a formatted table."""
    table = Table(title="Execution Plan", show_header=True)
    table.add_column("Step", style="cyan", width=6)
    table.add_column("Action", style="white")
    table.add_column("Source", style="green")

    for step in plan.steps:
        table.add_row(str(step.step), step.action, step.source or "-")

    console.print(Panel(f"[bold]Understanding:[/bold] {plan.query_understanding}"))
    console.print(table)

def display_memory(memory: dict, step: int, total: int) -> None:
    """Display current memory state and progress."""
    console.print(Panel(f"[bold cyan]Progress: Step {step}/{total}[/bold cyan]"))

    entries = memory.get("entries", [])
    if entries:
        table = Table(title="Memory State", show_header=True)
        table.add_column("Step", width=6)
        table.add_column("Source", width=15)
        table.add_column("Status", width=8)
        table.add_column("Result", overflow="fold")

        for entry in entries[-5:]:  # Last 5 entries
            content = entry.get("content", {})
            status = "[green]Y[/green]" if content.get("success") else "[red]X[/red]"
            result = content.get("result", content.get("error", ""))[:100]
            table.add_row(
                str(content.get("step", "?")),
                content.get("source", "-"),
                status,
                result,
            )
        console.print(table)


def display_execution_progress(
    step: int, total: int, code: str, result: str, source: str, success: bool
) -> None:
    """Display step execution progress."""
    status = "[green]Y[/green]" if success else "[red]X[/red]"
    console.print(f"  {status} Step {step}/{total} on [cyan]{source}[/cyan]")
    if code:
        console.print(
            Panel(
                Syntax(code, "python", theme="monokai", line_numbers=False),
                title="Code",
                border_style="dim",
            )
        )
    result_style = "green" if success else "red"
    console.print(Panel(result[:500], title="Result", border_style=result_style))
    console.print()  # spacing


def display_verification(verification: Verification, answer: str) -> None:
    """Display verification results."""
    console.print(Panel(answer, title="Answer", border_style="green"))

    table = Table(title="Verification", show_header=False)
    table.add_column("Metric", style="cyan")
    table.add_column("Value")

    complete_status = "[green]Yes[/green]" if verification.is_complete else "[red]No[/red]"
    accurate_status = "[green]Yes[/green]" if verification.is_accurate else "[red]No[/red]"

    table.add_row("Complete", complete_status)
    table.add_row("Accurate", accurate_status)
    table.add_row("Confidence", f"{verification.confidence_score:.0%}")
    table.add_row("Recommendation", verification.recommendation.upper())

    console.print(table)

    if verification.gaps:
        console.print(
            Panel(
                "\n".join(f"* {g}" for g in verification.gaps),
                title="Gaps",
                border_style="yellow",
            )
        )
    if verification.issues:
        console.print(
            Panel(
                "\n".join(f"* {i}" for i in verification.issues),
                title="Issues",
                border_style="red",
            )
        )
