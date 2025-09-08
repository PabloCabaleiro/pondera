"""Tests for pondera.api module."""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from pathlib import Path
from typing import Any

from pondera.api import evaluate_case_async, evaluate_case
from pondera.models.case import CaseSpec, CaseInput, CaseJudge
from pondera.models.evaluation import EvaluationResult
from pondera.models.judgment import Judgment
from pondera.models.run import RunResult
from pondera.models.rubric import RubricCriterion
from pondera.runner.base import ProgressCallback


class MockRunner:
    """Mock runner for testing."""

    def __init__(self, result: RunResult | None = None, delay: float = 0.0):
        self.result = result or RunResult(question="Test question", answer_markdown="Test answer")
        self.delay = delay
        self.call_count = 0
        self.last_call_args: dict[str, Any] | None = None

    async def run(
        self,
        *,
        question: str,
        attachments: list[str] | None = None,
        params: dict[str, Any] | None = None,
        progress: ProgressCallback | None = None,
    ) -> RunResult:
        self.call_count += 1
        self.last_call_args = {
            "question": question,
            "attachments": attachments,
            "params": params,
            "progress": progress,
        }

        if self.delay > 0:
            await asyncio.sleep(self.delay)

        return self.result


class MockJudge:
    """Mock judge for testing."""

    def __init__(self, judgment: Judgment | None = None, delay: float = 0.0):
        self.judgment = judgment or Judgment(
            score=85,  # Integer, not float
            pass_fail=True,  # Required field
            reasoning="Good answer",
            criteria_scores={"accuracy": 90, "clarity": 80},  # Integer scores
        )
        self.delay = delay
        self.call_count = 0
        self.last_call_args: dict[str, Any] | None = None

    async def judge(
        self,
        *,
        question: str,
        answer_markdown: str,
        judge_request: str | None = None,
        rubric: list[RubricCriterion] | None = None,
        model: str | None = None,
        system_append: str | None = None,
    ) -> Judgment:
        self.call_count += 1
        self.last_call_args = {
            "question": question,
            "answer_markdown": answer_markdown,
            "judge_request": judge_request,
            "rubric": rubric,
            "model": model,
            "system_append": system_append,
        }

        if self.delay > 0:
            await asyncio.sleep(self.delay)

        return self.judgment


@pytest.fixture
def sample_case() -> CaseSpec:
    """Sample case for testing."""
    return CaseSpec(
        id="test-case",
        input=CaseInput(
            query="What is the capital of France?",
            attachments=[],  # Empty list instead of None
            params={},  # Empty dict instead of None
        ),
        judge=CaseJudge(
            request="Judge the accuracy of this answer",
            rubric=None,
            overall_threshold=7.0,
            per_criterion_thresholds={},  # Empty dict instead of None
            model=None,
            system_append="",  # Empty string instead of None
        ),
    )


@pytest.fixture
def sample_rubric() -> list[RubricCriterion]:
    """Sample rubric for testing."""
    return [
        RubricCriterion(name="accuracy", description="How accurate is the answer?", weight=1.0),
        RubricCriterion(name="clarity", description="How clear is the answer?", weight=0.8),
    ]


class TestEvaluateCaseAsync:
    """Test the evaluate_case_async function."""

    @pytest.mark.asyncio
    async def test_evaluate_case_async_basic(self, sample_case: CaseSpec) -> None:
        """Test basic evaluation workflow."""
        runner = MockRunner()
        judge = MockJudge()

        with (
            patch("pondera.api.load_case_yaml", return_value=sample_case),
            patch("pondera.api.get_settings"),
            patch("pondera.api.apply_prejudge_checks", return_value=[]),
            patch("pondera.api.choose_rubric", return_value=None),
            patch("pondera.api.compute_pass", return_value=True),
        ):
            result = await evaluate_case_async("/fake/path.yaml", runner=runner, judge=judge)

        assert isinstance(result, EvaluationResult)
        assert result.case_id == "test-case"
        assert result.case == sample_case
        assert result.passed is True
        assert runner.call_count == 1
        assert judge.call_count == 1

    @pytest.mark.asyncio
    async def test_evaluate_case_async_with_progress(self, sample_case: CaseSpec) -> None:
        """Test evaluation with progress callback."""
        runner = MockRunner()
        judge = MockJudge()
        progress_callback = AsyncMock()

        with (
            patch("pondera.api.load_case_yaml", return_value=sample_case),
            patch("pondera.api.get_settings"),
            patch("pondera.api.apply_prejudge_checks", return_value=[]),
            patch("pondera.api.choose_rubric", return_value=None),
            patch("pondera.api.compute_pass", return_value=True),
        ):
            await evaluate_case_async(
                "/fake/path.yaml", runner=runner, judge=judge, progress=progress_callback
            )

        # Should have called progress for starting and judging
        assert progress_callback.call_count >= 2
        progress_callback.assert_any_call("pondera: running case 'test-case'…")
        progress_callback.assert_any_call("pondera: judging answer…")

    @pytest.mark.asyncio
    async def test_evaluate_case_async_with_default_rubric(
        self, sample_case: CaseSpec, sample_rubric: list[RubricCriterion]
    ) -> None:
        """Test evaluation with default rubric."""
        runner = MockRunner()
        judge = MockJudge()

        with (
            patch("pondera.api.load_case_yaml", return_value=sample_case),
            patch("pondera.api.get_settings"),
            patch("pondera.api.apply_prejudge_checks", return_value=[]),
            patch("pondera.api.choose_rubric", return_value=sample_rubric) as mock_choose,
            patch("pondera.api.compute_pass", return_value=True),
        ):
            await evaluate_case_async(
                "/fake/path.yaml", runner=runner, judge=judge, default_rubric=sample_rubric
            )

        # Verify choose_rubric was called with both case rubric and default
        mock_choose.assert_called_once_with(sample_case.judge.rubric, sample_rubric)

    @pytest.mark.asyncio
    async def test_evaluate_case_async_with_precheck_failures(self, sample_case: CaseSpec) -> None:
        """Test evaluation with precheck failures."""
        runner = MockRunner()
        judge = MockJudge()
        precheck_failures = ["Missing required keyword"]

        with (
            patch("pondera.api.load_case_yaml", return_value=sample_case),
            patch("pondera.api.get_settings"),
            patch("pondera.api.apply_prejudge_checks", return_value=precheck_failures),
            patch("pondera.api.choose_rubric", return_value=None),
            patch("pondera.api.compute_pass", return_value=False),
        ):
            result = await evaluate_case_async("/fake/path.yaml", runner=runner, judge=judge)

        assert result.precheck_failures == precheck_failures
        assert result.passed is False

    @pytest.mark.asyncio
    async def test_evaluate_case_async_timing_measurement(self, sample_case: CaseSpec) -> None:
        """Test that timing measurements are captured."""
        runner = MockRunner(delay=0.1)  # 100ms delay
        judge = MockJudge(delay=0.05)  # 50ms delay

        with (
            patch("pondera.api.load_case_yaml", return_value=sample_case),
            patch("pondera.api.get_settings"),
            patch("pondera.api.apply_prejudge_checks", return_value=[]),
            patch("pondera.api.choose_rubric", return_value=None),
            patch("pondera.api.compute_pass", return_value=True),
        ):
            result = await evaluate_case_async("/fake/path.yaml", runner=runner, judge=judge)

        # Check timing structure
        assert "runner_s" in result.timings_s
        assert "judge_s" in result.timings_s
        assert "total_s" in result.timings_s

        # Should have reasonable timing values (allowing for test overhead)
        assert result.timings_s["runner_s"] >= 0.09  # Should be close to 0.1s
        assert result.timings_s["judge_s"] >= 0.04  # Should be close to 0.05s
        assert result.timings_s["total_s"] >= 0.14  # Should be sum + overhead

    @pytest.mark.asyncio
    async def test_evaluate_case_async_passes_runner_parameters(
        self, sample_case: CaseSpec
    ) -> None:
        """Test that runner receives correct parameters."""
        # Modify case to have attachments and params
        case_with_params = CaseSpec(
            id="test-case",
            input=CaseInput(
                query="What is the capital of France?",
                attachments=["map.png", "facts.txt"],
                params={"language": "en", "detail_level": "high"},
            ),
            judge=sample_case.judge,
        )

        runner = MockRunner()
        judge = MockJudge()

        with (
            patch("pondera.api.load_case_yaml", return_value=case_with_params),
            patch("pondera.api.get_settings"),
            patch("pondera.api.apply_prejudge_checks", return_value=[]),
            patch("pondera.api.choose_rubric", return_value=None),
            patch("pondera.api.compute_pass", return_value=True),
        ):
            await evaluate_case_async("/fake/path.yaml", runner=runner, judge=judge)

        # Verify runner was called with correct parameters
        assert runner.last_call_args is not None
        assert runner.last_call_args["question"] == "What is the capital of France?"
        assert runner.last_call_args["attachments"] == ["map.png", "facts.txt"]
        assert runner.last_call_args["params"] == {"language": "en", "detail_level": "high"}

    @pytest.mark.asyncio
    async def test_evaluate_case_async_passes_judge_parameters(
        self, sample_case: CaseSpec, sample_rubric: list[RubricCriterion]
    ) -> None:
        """Test that judge receives correct parameters."""
        # Modify case to have judge parameters
        case_with_judge_params = CaseSpec(
            id="test-case",
            input=sample_case.input,
            judge=CaseJudge(
                request="Custom judge request",
                rubric=None,
                overall_threshold=8.0,
                per_criterion_thresholds={"accuracy": 9.0},
                model="gpt-4",
                system_append="Be extra strict",
            ),
        )

        runner = MockRunner()
        judge = MockJudge()

        with (
            patch("pondera.api.load_case_yaml", return_value=case_with_judge_params),
            patch("pondera.api.get_settings"),
            patch("pondera.api.apply_prejudge_checks", return_value=[]),
            patch("pondera.api.choose_rubric", return_value=sample_rubric),
            patch("pondera.api.compute_pass", return_value=True),
        ):
            await evaluate_case_async("/fake/path.yaml", runner=runner, judge=judge)

        # Verify judge was called with correct parameters
        assert judge.last_call_args is not None
        assert judge.last_call_args["question"] == "What is the capital of France?"
        assert judge.last_call_args["answer_markdown"] == "Test answer"
        assert judge.last_call_args["judge_request"] == "Custom judge request"
        assert judge.last_call_args["rubric"] == sample_rubric
        assert judge.last_call_args["model"] == "gpt-4"
        assert judge.last_call_args["system_append"] == "Be extra strict"

    @pytest.mark.asyncio
    async def test_evaluate_case_async_pathlib_path(self, sample_case: CaseSpec) -> None:
        """Test evaluation with pathlib.Path input."""
        runner = MockRunner()
        judge = MockJudge()
        case_path = Path("/fake/path.yaml")

        with (
            patch("pondera.api.load_case_yaml", return_value=sample_case),
            patch("pondera.api.get_settings"),
            patch("pondera.api.apply_prejudge_checks", return_value=[]),
            patch("pondera.api.choose_rubric", return_value=None),
            patch("pondera.api.compute_pass", return_value=True),
        ):
            result = await evaluate_case_async(case_path, runner=runner, judge=judge)

        assert isinstance(result, EvaluationResult)
        assert result.case_id == "test-case"


class TestEvaluateCase:
    """Test the synchronous evaluate_case function."""

    def test_evaluate_case_sync_wrapper(self, sample_case: CaseSpec) -> None:
        """Test that sync wrapper works correctly."""
        runner = MockRunner()
        judge = MockJudge()

        with (
            patch("pondera.api.load_case_yaml", return_value=sample_case),
            patch("pondera.api.get_settings"),
            patch("pondera.api.apply_prejudge_checks", return_value=[]),
            patch("pondera.api.choose_rubric", return_value=None),
            patch("pondera.api.compute_pass", return_value=True),
        ):
            result = evaluate_case("/fake/path.yaml", runner=runner, judge=judge)

        assert isinstance(result, EvaluationResult)
        assert result.case_id == "test-case"
        assert runner.call_count == 1
        assert judge.call_count == 1

    def test_evaluate_case_detects_running_loop(self, sample_case: CaseSpec) -> None:
        """Test that sync wrapper detects running event loop."""
        runner = MockRunner()
        judge = MockJudge()

        async def test_with_loop() -> None:
            # This should raise an error because we're in an async context
            with pytest.raises(RuntimeError) as exc_info:
                evaluate_case("/fake/path.yaml", runner=runner, judge=judge)

            assert "asyncio event loop is running" in str(exc_info.value)
            assert "evaluate_case_async" in str(exc_info.value)

        # Run the test in an async context
        asyncio.run(test_with_loop())

    def test_evaluate_case_with_all_parameters(
        self, sample_case: CaseSpec, sample_rubric: list[RubricCriterion]
    ) -> None:
        """Test sync wrapper with all parameters."""
        runner = MockRunner()
        judge = MockJudge()
        progress_callback = AsyncMock()

        with (
            patch("pondera.api.load_case_yaml", return_value=sample_case),
            patch("pondera.api.get_settings"),
            patch("pondera.api.apply_prejudge_checks", return_value=[]),
            patch("pondera.api.choose_rubric", return_value=sample_rubric),
            patch("pondera.api.compute_pass", return_value=True),
        ):
            result = evaluate_case(
                "/fake/path.yaml",
                runner=runner,
                judge=judge,
                default_rubric=sample_rubric,
                progress=progress_callback,
            )

        assert isinstance(result, EvaluationResult)
        assert result.case_id == "test-case"


class TestApiIntegration:
    """Integration tests for the API module."""

    @pytest.mark.asyncio
    async def test_end_to_end_evaluation_flow(
        self, sample_case: CaseSpec, sample_rubric: list[RubricCriterion]
    ) -> None:
        """Test complete evaluation flow with realistic data."""
        # Create runner that returns specific result
        run_result = RunResult(
            question="What is the capital of France?",
            answer_markdown="The capital of France is Paris.",
            artifacts=["source.txt"],
            metadata={"confidence": 0.95},
        )
        runner = MockRunner(result=run_result)

        # Create judge that returns specific judgment
        judgment = Judgment(
            score=92,  # Integer
            pass_fail=True,  # Required field
            reasoning="Accurate and concise answer.",
            criteria_scores={"accuracy": 100, "clarity": 85},  # Integer scores
        )
        judge = MockJudge(judgment=judgment)

        with (
            patch("pondera.api.load_case_yaml", return_value=sample_case),
            patch("pondera.api.get_settings"),
            patch("pondera.api.apply_prejudge_checks", return_value=[]),
            patch("pondera.api.choose_rubric", return_value=sample_rubric),
            patch("pondera.api.compute_pass", return_value=True),
        ):
            result = await evaluate_case_async(
                "/fake/path.yaml", runner=runner, judge=judge, default_rubric=sample_rubric
            )

        # Verify complete result structure
        assert result.case_id == "test-case"
        assert result.case == sample_case
        assert result.run == run_result
        assert result.judgment == judgment
        assert result.precheck_failures == []
        assert result.overall_threshold == 7.0
        assert result.per_criterion_thresholds == {}  # Empty dict from fixture
        assert result.passed is True
        assert "runner_s" in result.timings_s
        assert "judge_s" in result.timings_s
        assert "total_s" in result.timings_s
