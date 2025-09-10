from pydantic import BaseModel, Field, ConfigDict

# ─────────────────────────────────────────────────────────────────────────────
# Judge output (strict, typed)
# ─────────────────────────────────────────────────────────────────────────────


class Judgment(BaseModel):
    """
    Typed grading result from the judge.
    """

    model_config = ConfigDict(extra="forbid")

    score: int = Field(..., ge=0, le=100)
    pass_fail: bool
    reasoning: str
    criteria_scores: dict[str, int]  # e.g., {"correctness": 85, "completeness": 70, ...}
    issues: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
