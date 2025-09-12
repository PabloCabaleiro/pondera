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
    evaluation_passed: bool
    reasoning: str
    criteria_scores: dict[str, int]
    issues: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    judge_prompt: str = Field(default="")

    def __str__(self) -> str:  # pragma: no cover - trivial
        crit = sorted(self.criteria_scores.items())
        return (
            f"Judgment(score={self.score}, passed={self.evaluation_passed}, criteria={crit}, "
            f"issues={len(self.issues)}, suggestions={len(self.suggestions)})"
        )

    def __repr__(self) -> str:  # pragma: no cover - trivial
        reasoning_short = self.reasoning.strip().splitlines()[0][:60] if self.reasoning else ""
        return (
            f"Judgment(score={self.score}, evaluation_passed={self.evaluation_passed}, "
            f"criteria_scores={self.criteria_scores}, reasoning_snippet={reasoning_short!r})"
        )
