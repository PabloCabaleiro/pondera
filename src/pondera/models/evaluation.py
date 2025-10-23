from pydantic import BaseModel, Field, ConfigDict, model_validator
from pondera.models.run import RunResult
from pondera.models.judgment import Judgment
from pondera.models.case import CaseSpec


class EvaluationResult(BaseModel):
    """
    Aggregate result from running a case through a runner and a judge,
    including pre-judge checks and threshold evaluation.
    """

    model_config = ConfigDict(extra="ignore")

    case_id: str
    case: CaseSpec
    run: RunResult
    judgment: Judgment
    # Pre-judge textual checks outcome
    precheck_failures: list[str] = Field(default_factory=list)
    # Thresholds used at evaluation time
    overall_threshold: int
    per_criterion_thresholds: dict[str, int] = Field(default_factory=dict)
    # Final status computed by Pondera (independent of judgment.evaluation_passed)
    passed: bool
    # Optional timings in seconds
    timings_s: dict[str, float] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_threshold_keys(self) -> "EvaluationResult":
        pct = self.per_criterion_thresholds or {}
        if pct:
            score_keys = set(self.judgment.criteria_scores.keys())
            missing = set(pct.keys()) - score_keys
            if missing:
                raise ValueError(
                    "Invalid per_criterion_thresholds keys (unknown in criteria_scores: "
                    + ", ".join(sorted(missing))
                    + ")"
                )
        return self

    def __str__(self) -> str:  # pragma: no cover - trivial
        return (
            f"EvaluationResult(case_id={self.case_id}, passed={self.passed}, "
            f"overall_threshold={self.overall_threshold}, precheck_failures={len(self.precheck_failures)})"
        )

    def __repr__(self) -> str:  # pragma: no cover - trivial
        return (
            f"EvaluationResult(case_id={self.case_id!r}, passed={self.passed}, "
            f"score={self.judgment.score}, criteria={self.judgment.criteria_scores}, "
            f"failures={self.precheck_failures})"
        )
