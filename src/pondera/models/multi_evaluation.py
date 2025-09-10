from statistics import mean, median, pstdev, pvariance
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum
from pondera.models.evaluation import EvaluationResult


class AggregationMetric(str, Enum):
    min = "min"
    max = "max"
    mean = "mean"
    median = "median"


class ScoreAggregate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    metric: AggregationMetric = Field(description="Primary aggregation metric requested.")
    min: float
    max: float
    mean: float
    median: float
    stdev: float = Field(description="Population standard deviation (σ).")
    variance: float = Field(description="Population variance (σ²).")


def aggregate_numbers(values: list[float], metric: AggregationMetric) -> ScoreAggregate:
    """Aggregate a list of numeric values computing standard statistics."""
    if not values:
        raise ValueError("Cannot aggregate empty value list")
    return ScoreAggregate(
        metric=metric,
        min=min(values),
        max=max(values),
        mean=mean(values),
        median=median(values),
        stdev=pstdev(values) if len(values) > 1 else 0.0,
        variance=pvariance(values) if len(values) > 1 else 0.0,
    )


class CriteriaAggregates(BaseModel):
    model_config = ConfigDict(extra="forbid")
    overall: ScoreAggregate
    per_criterion: dict[str, ScoreAggregate]


class MultiEvaluationResult(BaseModel):
    """Result of executing the same case multiple times to measure reproducibility."""

    model_config = ConfigDict(extra="forbid")

    case_id: str
    evaluations: list[EvaluationResult] = Field(
        description="Individual evaluation runs (length = repetitions)."
    )
    aggregates: CriteriaAggregates
    passed: bool = Field(description="Pass/fail according to primary aggregation metric (overall).")
    primary_metric: AggregationMetric
