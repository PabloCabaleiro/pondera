# rubric.py

from pydantic import BaseModel, Field, ConfigDict, field_validator

# ─────────────────────────────────────────────────────────────────────────────
# Rubric
# ─────────────────────────────────────────────────────────────────────────────


class RubricCriterion(BaseModel):
    """One rubric axis: name, weight (>0), description."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1)
    weight: float = Field(..., gt=0.0)
    description: str = Field(..., min_length=1)


class Rubric(BaseModel):
    """A collection of rubric criteria."""

    model_config = ConfigDict(extra="forbid")

    rubric: list[RubricCriterion] = Field(default_factory=list)

    @field_validator("rubric")
    @classmethod
    def _non_empty(cls, v: list[RubricCriterion]) -> list[RubricCriterion]:
        if not v:
            raise ValueError("rubric must contain at least one criterion")
        return v

    def total_weight(self) -> float:
        return sum(c.weight for c in self.rubric)
