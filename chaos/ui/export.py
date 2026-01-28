"""Export run data to markdown format."""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class RunLogEntry:
    """Single entry in the run log."""

    timestamp: datetime
    agent: str  # "sensemaker", "info_seeker", "verifier", "user", "correction"
    action: str  # "request", "response", "correction_proposed", "correction_approved", etc.
    content: dict[str, Any]


@dataclass
class RunLog:
    """Accumulates all exchanges during a run for export."""

    query: str = ""
    plan: dict[str, Any] | None = None
    entries: list[RunLogEntry] = field(default_factory=list)
    final_answer: str = ""
    verification: dict[str, Any] | None = None
    start_time: datetime = field(default_factory=datetime.now)

    def add_entry(
        self,
        agent: str,
        action: str,
        content: dict[str, Any],
    ) -> None:
        """Add an entry to the run log."""
        self.entries.append(
            RunLogEntry(
                timestamp=datetime.now(),
                agent=agent,
                action=action,
                content=content,
            )
        )

    def set_plan(self, plan: Any) -> None:
        """Set the plan (from Plan model)."""
        if hasattr(plan, "model_dump"):
            self.plan = plan.model_dump()
        else:
            self.plan = dict(plan) if plan else None

    def set_verification(self, verification: Any) -> None:
        """Set the verification result."""
        if hasattr(verification, "model_dump"):
            self.verification = verification.model_dump()
        else:
            self.verification = dict(verification) if verification else None


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
                modified = " *(modified)*" if step.get("modified") else ""
                lines.append(f"| {step.get('step', '?')} | {action}{modified} | {source} |")
            lines.append(f"")

    # Execution Log
    lines.append(f"## Execution Log")
    lines.append(f"")

    iteration = 0
    for entry in run_log.entries:
        content = entry.content

        if entry.agent == "sensemaker" and entry.action == "request":
            iteration += 1
            lines.append(f"### Iteration {iteration}")
            lines.append(f"")
            lines.append(f"**Sensemaker Request:** {content.get('request', '')}")
            if content.get("reasoning"):
                lines.append(f"")
                lines.append(f"*Reasoning:* {content['reasoning']}")
            lines.append(f"")

        elif entry.agent == "info_seeker" and entry.action == "response":
            lines.append(f"**Info Seeker Response:**")
            lines.append(f"")
            lines.append(f"- **Source:** {content.get('source', 'unknown')}")
            lines.append(f"- **Success:** {'Yes' if content.get('success') else 'No'}")
            if include_code and content.get("code"):
                lines.append(f"")
                lines.append(f"```python")
                lines.append(content["code"])
                lines.append(f"```")
            lines.append(f"")
            lines.append(f"**Result:**")
            lines.append(f"```")
            result = content.get("result", "")
            # Truncate very long results
            if len(result) > 2000:
                result = result[:2000] + "\n... (truncated)"
            lines.append(result)
            lines.append(f"```")
            lines.append(f"")

        elif entry.agent == "correction" and entry.action == "proposed":
            lines.append(f"#### Data Quality Correction Proposed")
            lines.append(f"")
            lines.append(f"- **Affected Step:** {content.get('affected_step', '?')}")
            lines.append(f"- **Issue:** {content.get('issue_description', '')}")
            lines.append(f"- **Proposed Fix:** {content.get('proposed_correction', '')}")
            if content.get("reasoning"):
                lines.append(f"- **Reasoning:** {content['reasoning']}")
            lines.append(f"")

        elif entry.agent == "user" and entry.action == "correction_decision":
            decision = content.get("decision", "")
            lines.append(f"**User Decision:** {decision}")
            if decision == "modify" and content.get("modified_request"):
                lines.append(f"")
                lines.append(f"**Modified Request:** {content['modified_request']}")
            lines.append(f"")

        elif entry.agent == "sensemaker" and entry.action == "complete":
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
    output_path.write_text("\n".join(lines))
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
