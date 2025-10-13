"""Tests for runner error handling during evaluations."""

import pytest
from typing import Any
from unittest.mock import patch

from pondera.api import evaluate_case_async
from pondera.errors import RunnerError, TimeoutError
from pondera.models.case import CaseSpec, CaseInput, CaseJudge
from pondera.models.judgment import Judgment
from pondera.models.run import RunResult
from pondera.runner.base import ProgressCallback


class FailingRunner:
    """Mock runner that fails."""

    def __init__(self, exception: Exception):
        self.exception = exception
        self.call_count = 0

    async def run(
        self,
        *,
        question: str,
        attachments: list[str] | None = None,
        params: dict[str, Any] | None = None,
        progress: ProgressCallback | None = None,
    ) -> RunResult:
        self.call_count += 1
        raise self.exception


class ErrorCapturingJudge:
    """Mock judge that captures error information."""

    def __init__(self) -> None:
        self.call_count = 0
        self.last_error: str | None = None

    async def judge(
        self,
        *,
        question: str,
        answer: str,
        files: list[str] | None = None,
        judge_request: str | None = None,
        rubric: list | None = None,
        system_append: str | None = None,
        error: str | None = None,
    ) -> Judgment:
        self.call_count += 1
        self.last_error = error
        # Return a low score judgment for errors
        return Judgment(
            score=0,
            evaluation_passed=False,
            reasoning=f"Runner failed: {error}" if error else "No error",
            criteria_scores={"accuracy": 0},
        )


@pytest.fixture
def sample_case() -> CaseSpec:
    """Sample case for testing."""
    return CaseSpec(
        id="test-case",
        input=CaseInput(query="What is 2+2?", attachments=[], params={}),
        judge=CaseJudge(request="Evaluate the answer", rubric=None),
        timeout_s=5,
        repetitions=1,
    )


@pytest.mark.asyncio
async def test_runner_error_captured_and_passed_to_judge(sample_case: CaseSpec) -> None:
    """Test that runner errors are captured and passed to judge."""
    runner = FailingRunner(RunnerError("Connection failed"))
    judge = ErrorCapturingJudge()

    with (
        patch("pondera.api.load_case_yaml", return_value=sample_case),
        patch("pondera.api.get_settings"),
        patch("pondera.api.apply_prejudge_checks", return_value=[]),
        patch("pondera.api.choose_rubric", return_value=[]),
        patch("pondera.api.compute_pass", return_value=False),
    ):
        result = await evaluate_case_async("/fake/path.yaml", runner=runner, judge=judge)

        # Verify runner was called
        assert runner.call_count == 1

        # Verify judge received error information
        assert judge.call_count == 1
        assert judge.last_error is not None
        assert "RunnerError" in judge.last_error
        assert "Connection failed" in judge.last_error

        # Verify evaluation result contains error
        assert len(result.evaluations) == 1
        ev = result.evaluations[0]
        assert ev.run.error is not None
        assert "RunnerError" in ev.run.error
        assert ev.run.answer == ""


@pytest.mark.asyncio
async def test_timeout_error_captured_and_passed_to_judge(sample_case: CaseSpec) -> None:
    """Test that timeout errors are captured and passed to judge."""
    runner = FailingRunner(TimeoutError("Operation timed out after 5s"))
    judge = ErrorCapturingJudge()

    with (
        patch("pondera.api.load_case_yaml", return_value=sample_case),
        patch("pondera.api.get_settings"),
        patch("pondera.api.apply_prejudge_checks", return_value=[]),
        patch("pondera.api.choose_rubric", return_value=[]),
        patch("pondera.api.compute_pass", return_value=False),
    ):
        result = await evaluate_case_async("/fake/path.yaml", runner=runner, judge=judge)

        # Verify judge received timeout error
        assert judge.last_error is not None
        assert "TimeoutError" in judge.last_error
        assert "timed out" in judge.last_error

        # Verify result
        assert len(result.evaluations) == 1
        ev = result.evaluations[0]
        assert ev.run.error is not None
        assert "TimeoutError" in ev.run.error


@pytest.mark.asyncio
async def test_multiple_repetitions_with_some_failures(sample_case: CaseSpec) -> None:
    """Test that when running multiple repetitions, failures are captured individually."""

    class SometimesFailingRunner:
        """Runner that fails on odd attempts."""

        def __init__(self) -> None:
            self.call_count = 0

        async def run(
            self,
            *,
            question: str,
            attachments: list[str] | None = None,
            params: dict[str, Any] | None = None,
            progress: ProgressCallback | None = None,
        ) -> RunResult:
            self.call_count += 1
            if self.call_count % 2 == 1:  # Fail on 1st, 3rd, 5th...
                raise RunnerError(f"Failure on attempt {self.call_count}")
            return RunResult(question=question, answer="Success")

    runner = SometimesFailingRunner()
    judge = ErrorCapturingJudge()

    # Set repetitions to 3
    sample_case.repetitions = 3

    with (
        patch("pondera.api.load_case_yaml", return_value=sample_case),
        patch("pondera.api.get_settings"),
        patch("pondera.api.apply_prejudge_checks", return_value=[]),
        patch("pondera.api.choose_rubric", return_value=[]),
        patch("pondera.api.compute_pass", return_value=False),
    ):
        result = await evaluate_case_async("/fake/path.yaml", runner=runner, judge=judge)

        # Should have 3 evaluations
        assert len(result.evaluations) == 3

        # First attempt should have error
        assert result.evaluations[0].run.error is not None
        assert "attempt 1" in result.evaluations[0].run.error

        # Second attempt should succeed
        assert result.evaluations[1].run.error is None
        assert result.evaluations[1].run.answer == "Success"

        # Third attempt should have error
        assert result.evaluations[2].run.error is not None
        assert "attempt 3" in result.evaluations[2].run.error

        # Judge should have been called 3 times
        assert judge.call_count == 3


@pytest.mark.asyncio
async def test_runner_success_has_no_error(sample_case: CaseSpec) -> None:
    """Test that successful runs don't set error field."""

    class SuccessRunner:
        async def run(
            self,
            *,
            question: str,
            attachments: list[str] | None = None,
            params: dict[str, Any] | None = None,
            progress: ProgressCallback | None = None,
        ) -> RunResult:
            return RunResult(question=question, answer="Correct answer")

    runner = SuccessRunner()
    judge = ErrorCapturingJudge()

    with (
        patch("pondera.api.load_case_yaml", return_value=sample_case),
        patch("pondera.api.get_settings"),
        patch("pondera.api.apply_prejudge_checks", return_value=[]),
        patch("pondera.api.choose_rubric", return_value=[]),
        patch("pondera.api.compute_pass", return_value=True),
    ):
        result = await evaluate_case_async("/fake/path.yaml", runner=runner, judge=judge)

        # Verify no error was set
        assert len(result.evaluations) == 1
        ev = result.evaluations[0]
        assert ev.run.error is None
        assert ev.run.answer == "Correct answer"

        # Judge should not have received error
        assert judge.last_error is None
