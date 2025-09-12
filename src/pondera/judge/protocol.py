"""Judge protocol allowing custom judge implementations.

Users can implement their own judge without subclassing the built-in `Judge`.
The only required coroutine method is `judge`, which must return a `Judgment`.
"""

from typing import Protocol

from pondera.models.judgment import Judgment
from pondera.models.rubric import RubricCriterion


class JudgeProtocol(Protocol):
    """Minimal contract for a judge.

    Custom judges must implement a single async method `judge` with the
    same signature as the built-in judge class and return a `Judgment`.
    Implementations may ignore parameters they don't need (e.g. `files`).
    """

    async def judge(  # noqa: D401 - concise, signature is self-documenting
        self,
        *,
        question: str,
        answer: str,
        files: list[str] | None,
        judge_request: str,
        rubric: list[RubricCriterion] | None = None,
        system_append: str = "",
    ) -> Judgment: ...


__all__ = ["JudgeProtocol"]
