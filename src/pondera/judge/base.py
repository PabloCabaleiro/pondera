# src/pondera/judge/base.py
from typing import Protocol

from pondera.models.rubric import RubricCriterion
from pondera.models.judgment import Judgment


class JudgeError(RuntimeError):
    """Raised for judge configuration or runtime errors."""


class Judge(Protocol):
    """
    Minimal contract for a Pondera judge.
    Implementations score an answer per a rubric and return a structured Judgment.
    """

    async def judge(
        self,
        *,
        question: str,
        answer_markdown: str,
        judge_request: str,
        rubric: list[RubricCriterion] | None = None,
        model: str | None = None,
        system_append: str = "",
    ) -> Judgment: ...


def rubric_to_markdown(rubric: list[RubricCriterion]) -> str:
    """
    Render a rubric into concise markdown bullet points with weights.
    """
    return "\n".join(f"- **{c.name}** (w={c.weight:g}): {c.description}" for c in rubric)


def default_rubric() -> list[RubricCriterion]:
    """
    Default rubric used when none is provided.
    Kept "private" by convention but importable by implementations.
    """
    return [
        RubricCriterion(
            name="correctness",
            weight=0.40,
            description="Facts and computations are accurate; no hallucinations.",
        ),
        RubricCriterion(
            name="completeness",
            weight=0.25,
            description="Addresses the question fully with sufficient depth.",
        ),
        RubricCriterion(
            name="methodology_repro",
            weight=0.15,
            description="Steps/parameters clear enough to reproduce.",
        ),
        RubricCriterion(
            name="safety_compliance",
            weight=0.10,
            description="No unsafe/PHI/proprietary content.",
        ),
        RubricCriterion(
            name="presentation",
            weight=0.10,
            description="Clear structure and formatting.",
        ),
    ]


def rubric_weight_note(rubric: list[RubricCriterion]) -> str:
    """
    Brief instruction for how to handle non-normalized weights.
    """
    tw = sum(c.weight for c in rubric)
    return f"(If weights do not sum to 1, normalize by total weight {tw:g}.)"
