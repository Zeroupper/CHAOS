"""Pydantic models for CHAOS data structures."""

from typing import Literal

from pydantic import BaseModel, Field


# === Result Constants ===

REJECTED_RESULT: dict[str, str | None] = {"answer": None, "status": "rejected"}
CANCELLED_RESULT: dict[str, str | None] = {"answer": None, "status": "cancelled"}


# === Execution Results ===


class ExecutionResult(BaseModel):
    """Result from data source code execution."""

    result: str | None = None
    error: str | None = None
    truncated: bool = False

    @property
    def success(self) -> bool:
        return self.error is None


# === Plan Types ===


class PlanStep(BaseModel):
    """Single step in an execution plan."""

    step: int = Field(ge=1)
    action: str = Field(min_length=1)
    source: str = ""
    modified: bool = False  # True if user modified this step in interactive mode


class Plan(BaseModel):
    """Execution plan from planner."""

    query: str = ""
    query_understanding: str = ""
    required_info: list[str] = Field(default_factory=list)
    data_sources: list[str] = Field(default_factory=list)
    steps: list[PlanStep] = Field(default_factory=list)

    def format_steps(self, show_modified: bool = True, prefix: str = "  ") -> str:
        """
        Format plan steps as a string.

        Args:
            show_modified: Whether to show [USER MODIFIED] prefix for modified steps.
            prefix: Prefix for each line.

        Returns:
            Formatted string of steps.
        """
        if not self.steps:
            return f"{prefix}No specific steps in plan."

        lines = []
        for step in self.steps:
            source_str = f" (from {step.source})" if step.source else ""
            if step.modified and show_modified:
                lines.append(f"{prefix}Step {step.step} [USER MODIFIED]: {step.action}{source_str}")
            else:
                lines.append(f"{prefix}Step {step.step}: {step.action}{source_str}")
        return "\n".join(lines)


# === Step State Types ===


class StepState(BaseModel):
    """State tracking for a plan step."""

    step: int
    status: Literal["pending", "completed", "needs_clarification", "failed"] = "pending"
    result: str | None = None
    error: str | None = None
    clarification_request: str | None = None  # What clarification was asked
    clarification_response: str | None = None  # What the clarification revealed
    failure_reason: str | None = None  # Why the step failed (after clarification)

    @classmethod
    def from_result(
        cls,
        step: int,
        status: Literal["pending", "completed", "needs_clarification", "failed"],
        result: str | None = None,
        previous: "StepState | None" = None,
        **kwargs: str | None,
    ) -> "StepState":
        """
        Factory method to create StepState with optional inheritance from previous state.

        Args:
            step: Step number.
            status: New status.
            result: Result string.
            previous: Previous state to inherit clarification fields from.
            **kwargs: Additional fields (failure_reason, error, etc.)
        """
        base: dict[str, int | str | None] = {"step": step, "status": status, "result": result}
        if previous:
            base["clarification_request"] = previous.clarification_request
            base["clarification_response"] = previous.clarification_response
        return cls(**{**base, **kwargs})


# === Information Seeker Types ===


class QueryDecision(BaseModel):
    """LLM decision about which query to execute."""

    source: str = Field(min_length=1)
    query_type: Literal["exec"] = "exec"
    params: dict[str, str] = Field(default_factory=dict)


class InfoSeekerResult(BaseModel):
    """Result from information seeker."""

    request: str
    source: str
    query_type: str
    params: dict[str, str]
    results: str  # JSON string or error message
    success: bool


# === Sensemaker Response Types ===


class CompleteResponse(BaseModel):
    """Response when sensemaker has completed the task."""

    status: Literal["complete"] = "complete"
    answer: str = ""
    supporting_evidence: list[str] = Field(default_factory=list)


class NeedsInfoResponse(BaseModel):
    """Response when sensemaker needs more information."""

    status: Literal["needs_info"] = "needs_info"
    current_step: int = Field(ge=1, default=1)
    request: str = ""
    reasoning: str = ""


class NeedsCorrectionResponse(BaseModel):
    """Response when sensemaker detects data quality issue and proposes fix."""

    status: Literal["needs_correction"] = "needs_correction"
    affected_step: int = Field(ge=1)
    issue_description: str = ""
    proposed_correction: str = ""
    reasoning: str = ""


# Discriminated union - Instructor handles this automatically
SensemakerResponse = CompleteResponse | NeedsInfoResponse | NeedsCorrectionResponse


# === Verifier Types ===


class Verification(BaseModel):
    """Verification result from verifier."""

    is_complete: bool = False
    is_accurate: bool = False
    confidence_score: float = Field(ge=0.0, le=1.0, default=0.0)
    gaps: list[str] = Field(default_factory=list)
    issues: list[str] = Field(default_factory=list)
    summary: str = ""
    recommendation: Literal["approve", "reject", "needs_review"] = "needs_review"


class RecoveryGuidance(BaseModel):
    """Guidance for recovering from query execution errors."""

    summary: str = ""
    analysis: str = ""
    revised_request: str = ""
    guidance: str = ""


# === Sensemaker Get Answer Types ===


class FinalAnswer(BaseModel):
    """Final answer from sensemaker when get_answer is called."""

    answer: str = ""
    supporting_evidence: list[str] = Field(default_factory=list)
