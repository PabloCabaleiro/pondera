"""Integration helper runner implementations for integration tests.

Provides small deterministic runner classes used by integration test suites.
"""

from __future__ import annotations

from typing import Any

from pondera.models.run import RunResult
from pondera.runner.base import ProgressCallback


class TestRunner:
    __test__ = False
    """Return a fixed response for any question (predictable for assertions)."""

    def __init__(self, response: str = "This is a test response") -> None:
        self.response = response

    async def run(
        self,
        *,
        question: str,
        attachments: list[str] | None = None,
        params: dict[str, Any] | None = None,
        progress: ProgressCallback | None = None,
    ) -> RunResult:
        return RunResult(
            question=question,
            answer=self.response,
            metadata={"test": True, "params": params or {}},
        )


class MathTestRunner:
    """Very small arithmetic runner used in integration tests."""

    async def run(
        self,
        *,
        question: str,
        attachments: list[str] | None = None,
        params: dict[str, Any] | None = None,
        progress: ProgressCallback | None = None,
    ) -> RunResult:
        if "2 + 2" in question:
            answer = "4"
        elif "3 * 3" in question:
            answer = "9"
        elif "10 / 2" in question:
            answer = "5"
        else:
            answer = "I can only solve simple arithmetic problems like 2+2, 3*3, or 10/2"
        return RunResult(
            question=question,
            answer=answer,
            metadata={"solver": "simple_math", "params": params or {}},
        )


def get_test_runner() -> TestRunner:
    return TestRunner()


def get_math_runner() -> MathTestRunner:
    return MathTestRunner()
