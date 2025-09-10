from pydantic import BaseModel, Field, ConfigDict
from pondera.models.run import RunResult
from pondera.models.judgment import Judgment
from pondera.models.case import CaseSpec


class EvaluationResult(BaseModel):
    """
    Aggregate result from running a case through a runner and a judge,
    including pre-judge checks and threshold evaluation.
    """

    model_config = ConfigDict(extra="forbid")

    case_id: str
    case: CaseSpec
    run: RunResult
    judgment: Judgment
    # Pre-judge textual checks outcome
    precheck_failures: list[str] = Field(default_factory=list)
    # Thresholds used at evaluation time
    overall_threshold: int
    per_criterion_thresholds: dict[str, int] = Field(default_factory=dict)
    # Final status computed by Pondera (independent of judgment.pass_fail)
    passed: bool
    # Optional timings in seconds
    timings_s: dict[str, float] = Field(default_factory=dict)
