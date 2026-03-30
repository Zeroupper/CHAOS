"""Export run data to markdown format."""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..types import Verification


@dataclass
class RunLogEntry:
    """Single entry in the run log."""

    timestamp: datetime
    source: str  # "sensemaker", "info_seeker", "verifier", "user", "review"
    action: str  # "request", "response", "proposed", "review_decision", "complete"
    content: dict[str, Any]


@dataclass
class ExplorationTurn:
    """Single exploration turn from the ExplorerAgent."""

    turn: int
    source: str
    reasoning: str
    code: str
    result: str
    success: bool


@dataclass
class RunLog:
    """Accumulates all exchanges during a run for export."""

    query: str = ""
    plan: dict[str, Any] | None = None
    exploration: list[ExplorationTurn] = field(default_factory=list)
    data_context: str = ""  # Full explorer output passed to planner
    entries: list[RunLogEntry] = field(default_factory=list)
    final_answer: str = ""
    verification: dict[str, Any] | None = None
    start_time: datetime = field(default_factory=datetime.now)
    export_path: str | None = None

    def add_entry(
        self,
        source: str,
        action: str,
        content: dict[str, Any],
    ) -> None:
        """Add an entry to the run log."""
        self.entries.append(
            RunLogEntry(
                timestamp=datetime.now(),
                source=source,
                action=action,
                content=content,
            )
        )

    def set_plan(self, plan: Any) -> None:
        """Set the plan (from Plan Pydantic model)."""
        self.plan = plan.model_dump()

    def set_verification(self, verification: Any) -> None:
        """Set the verification result (from Verification Pydantic model)."""
        self.verification = verification.model_dump()


def export_run_to_markdown(
    run_log: RunLog,
    output_path: Path | str,
    include_code: bool = True,
) -> Path:
    """
    Export a run log to a markdown file.

    Args:
        run_log: The run log to export.
        output_path: Path to write the markdown file.
        include_code: Whether to include code blocks.

    Returns:
        Path to the created file.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []

    # Header
    lines.append(f"# CHAOS Run Export")
    lines.append(f"")
    lines.append(f"**Date:** {run_log.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"")

    # Query
    lines.append(f"## Query")
    lines.append(f"")
    lines.append(f"> {run_log.query}")
    lines.append(f"")

    # Exploration
    if run_log.exploration:
        lines.append(f"## Data Exploration")
        lines.append(f"")
        for exp in run_log.exploration:
            status = "OK" if exp.success else "FAILED"
            lines.append(f"### Turn {exp.turn} — `{exp.source}` [{status}]")
            lines.append(f"")
            lines.append(f"**Reasoning:** {exp.reasoning}")
            lines.append(f"")
            lines.append(f"```python")
            lines.append(exp.code)
            lines.append(f"```")
            lines.append(f"")
            result_text = exp.result
            if len(result_text) > 2000:
                result_text = result_text[:2000] + "\n... (truncated)"
            lines.append(f"**Result:**")
            lines.append(f"```")
            lines.append(result_text)
            lines.append(f"```")
            lines.append(f"")

    # Data Context (what the planner received from the explorer)
    if run_log.data_context:
        lines.append(f"## Data Context (Explorer → Planner)")
        lines.append(f"")
        ctx = run_log.data_context
        if len(ctx) > 5000:
            ctx = ctx[:5000] + "\n... (truncated)"
        lines.append(f"```")
        lines.append(ctx)
        lines.append(f"```")
        lines.append(f"")

    # Plan
    if run_log.plan:
        lines.append(f"## Plan")
        lines.append(f"")
        if run_log.plan.get("query_understanding"):
            lines.append(f"**Understanding:** {run_log.plan['query_understanding']}")
            lines.append(f"")
        steps = run_log.plan.get("steps", [])
        if steps:
            lines.append(f"| Step | Action | Source |")
            lines.append(f"|------|--------|--------|")
            for step in steps:
                action = step.get("action", "").replace("|", "\\|")
                source = step.get("source", "-") or "-"
                lines.append(f"| {step.get('step', '?')} | {action} | {source} |")
            lines.append(f"")

    # Execution Log
    lines.append(f"## Execution Log")
    lines.append(f"")

    for entry in run_log.entries:
        content = entry.content

        if entry.source == "sensemaker" and entry.action == "request":
            lines.append(f"")
            lines.append(f"**Sensemaker Request:** {content.get('request', '')}")
            if content.get("reasoning"):
                lines.append(f"")
                lines.append(f"*Reasoning:* {content['reasoning']}")
            lines.append(f"")

        elif entry.source == "info_seeker" and entry.action == "response":
            lines.append(f"**Info Seeker Response:**")
            lines.append(f"")
            lines.append(f"- **Source:** {content.get('source', 'unknown')}")
            lines.append(f"- **Success:** {'Yes' if content.get('success') else 'No'}")
            code = content.get("params", {}).get("code", "")
            if include_code and code:
                lines.append(f"")
                lines.append(f"```python")
                lines.append(code)
                lines.append(f"```")
            lines.append(f"")
            lines.append(f"**Result:**")
            lines.append(f"```")
            result = content.get("results", "")
            # Truncate very long results
            if len(result) > 2000:
                result = result[:2000] + "\n... (truncated)"
            lines.append(result)
            lines.append(f"```")
            lines.append(f"")

        elif entry.source == "review" and entry.action == "proposed":
            lines.append(f"#### Data Quality Review Proposed")
            lines.append(f"")
            lines.append(f"- **Affected Step:** {content.get('affected_step', '?')}")
            lines.append(f"- **Issue:** {content.get('issue_description', '')}")
            lines.append(f"- **Proposed Fix:** {content.get('proposed_correction', '')}")
            if content.get("reasoning"):
                lines.append(f"- **Reasoning:** {content['reasoning']}")
            lines.append(f"")

        elif entry.source == "user" and entry.action == "review_decision":
            decision = content.get("decision", "")
            lines.append(f"**User Decision:** {decision}")
            if decision == "modify" and content.get("modified_request"):
                lines.append(f"")
                lines.append(f"**Modified Request:** {content['modified_request']}")
            lines.append(f"")

        elif entry.source == "sensemaker" and entry.action == "complete":
            lines.append(f"### Sensemaker Complete")
            lines.append(f"")

    # Final Answer
    lines.append(f"## Final Answer")
    lines.append(f"")
    lines.append(f"```")
    lines.append(run_log.final_answer or "(No answer)")
    lines.append(f"```")
    lines.append(f"")

    # Verification
    if run_log.verification:
        lines.append(f"## Verification")
        lines.append(f"")
        v = run_log.verification
        lines.append(f"| Metric | Value |")
        lines.append(f"|--------|-------|")
        lines.append(f"| Complete | {'Yes' if v.get('is_complete') else 'No'} |")
        lines.append(f"| Accurate | {'Yes' if v.get('is_accurate') else 'No'} |")
        lines.append(f"| Confidence | {v.get('confidence_score', 0):.0%} |")
        lines.append(f"| Recommendation | {v.get('recommendation', 'unknown').upper()} |")
        lines.append(f"")

        if v.get("gaps"):
            lines.append(f"**Gaps:**")
            for gap in v["gaps"]:
                lines.append(f"- {gap}")
            lines.append(f"")

        if v.get("issues"):
            lines.append(f"**Issues:**")
            for issue in v["issues"]:
                lines.append(f"- {issue}")
            lines.append(f"")

        if v.get("summary"):
            lines.append(f"**Summary:** {v['summary']}")
            lines.append(f"")

    # Write file
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def generate_run_filename(query: str, output_dir: Path | str = ".") -> Path:
    """
    Generate a filename for a run export based on query and timestamp.

    Args:
        query: The original query.
        output_dir: Directory to put the file in.

    Returns:
        Path for the export file.
    """
    output_dir = Path(output_dir)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Create a safe filename from query
    safe_query = "".join(c if c.isalnum() or c in " -_" else "" for c in query[:40])
    safe_query = safe_query.strip().replace(" ", "_")
    if not safe_query:
        safe_query = "run"
    return output_dir / f"{timestamp}_{safe_query}.md"


def export_verbose_transcript(
    transcript: list[dict],
    output_path: Path | str,
) -> Path:
    """
    Export the full LLM transcript (prompts + responses) to a markdown file.

    Args:
        transcript: List of transcript entries from StructuredLLMClient.
        output_path: Path to write the markdown file.

    Returns:
        Path to the created file.
    """
    import json

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []
    lines.append("# CHAOS Verbose Transcript")
    lines.append("")

    for i, entry in enumerate(transcript, 1):
        agent = entry.get("agent", "Unknown")
        lines.append(f"## Call {i}: {agent}")
        lines.append("")

        ts = entry.get("timestamp", "")
        if ts:
            lines.append(f"**Timestamp:** {ts}")
            lines.append("")

        system_prompt = entry.get("system_prompt")
        if system_prompt:
            lines.append("### System Prompt")
            lines.append("")
            lines.append("```")
            lines.append(system_prompt)
            lines.append("```")
            lines.append("")

        messages = entry.get("messages", [])
        if messages:
            lines.append("### Messages")
            lines.append("")
            for msg in messages:
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                lines.append(f"**{role}:**")
                lines.append("")
                lines.append("```")
                lines.append(content)
                lines.append("```")
                lines.append("")

        response = entry.get("response")
        if response:
            lines.append("### Response")
            lines.append("")
            lines.append("```json")
            lines.append(json.dumps(response, indent=2, default=str))
            lines.append("```")
            lines.append("")

        lines.append("---")
        lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def offer_export_to_user(
    run_log: RunLog,
    result: dict[str, Any],
    verification: "Verification | None",
    export_dir: str | None,
    auto_approve: bool = False,
) -> None:
    """
    Offer to export the run to a markdown file.

    Args:
        run_log: The run log to export.
        result: The result dictionary.
        verification: Verification result if available.
        export_dir: Directory for exports. Defaults to "exported_runs" if None.
        auto_approve: If True, automatically save without prompting.
    """
    from .display import console
    from .prompts import prompt_export_run

    # Update run log with final data
    if not run_log.final_answer:
        run_log.final_answer = result.get("answer", "")
    if verification:
        run_log.set_verification(verification)

    # Use exported_runs directory if no export_dir specified
    output_dir = export_dir or "exported_runs"

    # Generate default filename
    default_path = str(generate_run_filename(run_log.query, output_dir))

    # Auto-save or prompt user
    if auto_approve:
        export_path = default_path
    else:
        export_path = prompt_export_run(default_path)

    if export_path:
        try:
            output = export_run_to_markdown(run_log, export_path)
            run_log.export_path = str(output)
            console.print(f"\n[green]Run exported to:[/green] {output}")
        except Exception as e:
            console.print(f"\n[red]Failed to export run:[/red] {e}")
