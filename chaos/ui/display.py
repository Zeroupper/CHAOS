"""Rich-based display components for CHAOS."""

from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from ..types import Plan, StepState, Verification

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

def display_memory_table(memory: dict) -> None:
    """Display memory state as a formatted table showing executed code and results."""
    entries = memory.get("entries", [])
    if not entries:
        console.print("[dim]Memory: empty[/dim]")
        return

    table = Table(title="Memory State", show_header=True, expand=True)
    table.add_column("Step", style="cyan", width=5, justify="center")
    table.add_column("Code", style="dim", overflow="fold")
    table.add_column("Result", max_width=60, overflow="fold")

    for entry in entries:
        content = entry.get("content", {})
        if isinstance(content, dict) and "step" in content:
            step = str(content.get("step", "?"))
            success = content.get("success", False)

            code = content.get("code", "-")

            result = content.get("result") if success else content.get("error", "")
            if result:
                result = str(result)
            else:
                result = "-"

            table.add_row(step, code, result)

    console.print(table)


def display_step_states(step_states: dict[int, StepState], plan: Plan | None = None) -> None:
    """Display step states as a formatted table showing step descriptions."""
    if not step_states:
        return

    table = Table(title="Step States", show_header=True, expand=True)
    table.add_column("Step", style="cyan", width=5, justify="center")
    table.add_column("Description", overflow="fold")

    # Build step descriptions from plan
    step_descriptions: dict[int, str] = {}
    if plan:
        for step in plan.steps:
            step_descriptions[step.step] = step.action

    for step_num in sorted(step_states.keys()):
        description = step_descriptions.get(step_num, "-")
        table.add_row(str(step_num), description)

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


def display_tool_execution(
    tool_name: str,
    params: dict[str, Any] | None = None,
    result: dict[str, Any] | None = None,
    success: bool = True
) -> None:
    """Display tool execution status."""
    status_icon = "[green]✓[/green]" if success else "[red]✗[/red]"
    console.print(
        f"{status_icon} Tool: [cyan]{tool_name}[/cyan]"
    )

    if params:
        # Show key params (not all)
        key_params = {k: v for k, v in params.items() if k in ["query", "url", "max_results"]}
        if key_params:
            params_str = ", ".join(f"{k}={repr(v)[:30]}" for k, v in key_params.items())
            console.print(f"   Params: [dim]{params_str}[/dim]")

    if result and not success:
        error = result.get("error", "Unknown error")
        console.print(f"   [red]Error: {error}[/red]")

    console.print()
