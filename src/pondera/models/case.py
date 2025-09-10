from typing import Any

from pydantic import BaseModel, Field, ConfigDict
from pondera.models.rubric import RubricCriterion

# ─────────────────────────────────────────────────────────────────────────────
# Case expectations (pre-judge checks)
# ─────────────────────────────────────────────────────────────────────────────


class CaseExpectations(BaseModel):
    """Pre-judge assertions against the produced answer text/markdown."""

    model_config = ConfigDict(extra="forbid")

    must_contain: list[str] = Field(default_factory=list)
    must_not_contain: list[str] = Field(default_factory=list)
    regex_must_match: list[str] = Field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# Case input (what the runner will receive)
# ─────────────────────────────────────────────────────────────────────────────


class CaseInput(BaseModel):
    """Inputs forwarded to the runner."""

    model_config = ConfigDict(extra="forbid")

    query: str = Field(..., min_length=1)
    attachments: list[str] = Field(default_factory=list)  # file paths (optional)
    params: dict[str, Any] = Field(default_factory=dict)  # free-form runner params


# ─────────────────────────────────────────────────────────────────────────────
# Judge configuration (LLM-as-a-judge; model-agnostic)
# ─────────────────────────────────────────────────────────────────────────────


class CaseJudge(BaseModel):
    """How to evaluate the answer (per-case overrides allowed)."""

    model_config = ConfigDict(extra="forbid")

    request: str = Field(
        default="Judge for factual correctness, completeness, and clarity. "
        "Return strict JSON for the Judgment schema."
    )
    overall_threshold: int = Field(default=70, ge=0, le=100)
    per_criterion_thresholds: dict[str, int] = Field(default_factory=dict)
    rubric: list[RubricCriterion] | None = None  # overrides project default rubric
    system_append: str = Field(default="")  # extra system guidance for the judge


# ─────────────────────────────────────────────────────────────────────────────
# Case spec (the YAML file maps to this)
# ─────────────────────────────────────────────────────────────────────────────


class CaseSpec(BaseModel):
    """Full case definition loaded from YAML."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., min_length=1)
    input: CaseInput
    expect: CaseExpectations = Field(default_factory=CaseExpectations)
    judge: CaseJudge = Field(default_factory=CaseJudge)
    timeout_s: int = Field(default=240, gt=0)
    repetitions: int = Field(
        default=1, ge=1, description="Number of repeated executions for reproducibility stats."
    )
