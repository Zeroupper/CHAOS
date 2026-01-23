"""Pydantic models for CHAOS data structures."""

from typing import Literal

from pydantic import BaseModel, Field


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
    success_criteria: list[str] = Field(default_factory=list)


# === Memory Types ===


class StepMemoryEntry(BaseModel):
    """Memory entry for a completed step."""

    step: int
    source: str
    success: bool
    code: str | None = None
    result: str | None = None
    error: str | None = None


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

    def to_memory_entry(self, step: int) -> StepMemoryEntry:
        """Convert to memory entry for sensemaker."""
        return StepMemoryEntry(
            step=step,
            source=self.source,
            success=self.success,
            code=self.params.get("code"),
            result=self.results if self.success else None,
            error=self.results if not self.success else None,
        )


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


# Discriminated union - Instructor handles this automatically
SensemakerResponse = CompleteResponse | NeedsInfoResponse


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
