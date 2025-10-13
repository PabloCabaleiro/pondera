"""Tests for pondera.api module."""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from pathlib import Path
from typing import Any

from pondera.api import evaluate_case_async, evaluate_case
from pondera.errors import ValidationError
from pondera.models.case import CaseSpec, CaseInput, CaseJudge
from pondera.models.judgment import Judgment
from pondera.models.run import RunResult
from pondera.models.rubric import RubricCriterion
from pondera.models.multi_evaluation import MultiEvaluationResult, AggregationMetric
from pondera.runner.base import ProgressCallback


class MockRunner:
    """Mock runner for testing."""

    def __init__(self, result: RunResult | None = None, delay: float = 0.0):
        self.result = result or RunResult(question="Test question", answer="Test answer")
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
            evaluation_passed=True,  # Required field
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
        answer: str,
        files: list[str] | None = None,
        judge_request: str | None = None,
        rubric: list[RubricCriterion] | None = None,
        model: str | None = None,
        system_append: str | None = None,
        error: str | None = None,
    ) -> Judgment:
        self.call_count += 1
        self.last_call_args = {
            "question": question,
            "answer": answer,
            "files": files,
            "judge_request": judge_request,
            "rubric": rubric,
            "system_append": system_append,
            "error": error,
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
            assert isinstance(result, MultiEvaluationResult)
            assert len(result.evaluations) == 1
            single = result.evaluations[0]
            assert single.case_id == "test-case"
            assert single.case == sample_case
            assert result.passed is True
        assert runner.call_count == 1
        assert judge.call_count == 1

    @pytest.mark.asyncio
    async def test_evaluate_case_async_with_progress(self, sample_case: CaseSpec) -> None:
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
        assert progress_callback.call_count >= 2
        progress_callback.assert_any_call("pondera: running case 'test-case'…")
        progress_callback.assert_any_call("pondera: judging answer…")

    @pytest.mark.asyncio
    async def test_evaluate_case_async_with_default_rubric(
        self, sample_case: CaseSpec, sample_rubric: list[RubricCriterion]
    ) -> None:
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
        mock_choose.assert_called_once_with(sample_case.judge.rubric, sample_rubric)

    @pytest.mark.asyncio
    async def test_evaluate_case_async_with_precheck_failures(self, sample_case: CaseSpec) -> None:
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
            assert isinstance(result, MultiEvaluationResult)
            ev = result.evaluations[0]
            assert ev.precheck_failures == precheck_failures
            # MultiEvaluationResult.passed is based on aggregated scores only; evaluation-level pass reflects precheck failure logic
            assert ev.passed is False

    @pytest.mark.asyncio
    async def test_evaluate_case_async_timing_measurement(self, sample_case: CaseSpec) -> None:
        runner = MockRunner(delay=0.1)
        judge = MockJudge(delay=0.05)
        with (
            patch("pondera.api.load_case_yaml", return_value=sample_case),
            patch("pondera.api.get_settings"),
            patch("pondera.api.apply_prejudge_checks", return_value=[]),
            patch("pondera.api.choose_rubric", return_value=None),
            patch("pondera.api.compute_pass", return_value=True),
        ):
            result = await evaluate_case_async("/fake/path.yaml", runner=runner, judge=judge)
            assert isinstance(result, MultiEvaluationResult)
            ev = result.evaluations[0]
            assert "runner_s" in ev.timings_s
            assert "judge_s" in ev.timings_s
            assert "total_s" in ev.timings_s
            assert ev.timings_s["runner_s"] >= 0.09
            assert ev.timings_s["judge_s"] >= 0.04
            assert ev.timings_s["total_s"] >= 0.14

    @pytest.mark.asyncio
    async def test_evaluate_case_async_passes_runner_parameters(
        self, sample_case: CaseSpec
    ) -> None:
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
        assert runner.last_call_args is not None
        assert runner.last_call_args["question"] == "What is the capital of France?"
        assert runner.last_call_args["attachments"] == ["map.png", "facts.txt"]
        assert runner.last_call_args["params"] == {"language": "en", "detail_level": "high"}

    @pytest.mark.asyncio
    async def test_evaluate_case_async_passes_judge_parameters(
        self, sample_case: CaseSpec, sample_rubric: list[RubricCriterion]
    ) -> None:
        case_with_judge_params = CaseSpec(
            id="test-case",
            input=sample_case.input,
            judge=CaseJudge(
                request="Custom judge request",
                rubric=None,
                overall_threshold=8.0,
                per_criterion_thresholds={"accuracy": 9.0},
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
        assert judge.last_call_args is not None
        assert judge.last_call_args["question"] == "What is the capital of France?"
        assert judge.last_call_args["answer"] == "Test answer"
        assert judge.last_call_args["judge_request"] == "Custom judge request"
        assert judge.last_call_args["rubric"] == sample_rubric
        assert judge.last_call_args["system_append"] == "Be extra strict"

    @pytest.mark.asyncio
    async def test_evaluate_case_async_pathlib_path(self, sample_case: CaseSpec) -> None:
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
            assert isinstance(result, MultiEvaluationResult)
            assert len(result.evaluations) == 1
            single = result.evaluations[0]
            assert single.case_id == "test-case"

    @pytest.mark.asyncio
    async def test_evaluate_case_async_multi_repetitions(self, sample_case: CaseSpec) -> None:
        multi_case = CaseSpec(
            id=sample_case.id,
            input=sample_case.input,
            judge=sample_case.judge,
            repetitions=3,
        )
        scores = [70, 80, 90]

        class VaryJudge(MockJudge):
            def __init__(self) -> None:
                self.idx = 0

            async def judge(self, **kwargs: Any) -> Judgment:
                sc = scores[self.idx]
                self.idx += 1
                return Judgment(
                    score=sc,
                    evaluation_passed=True,
                    reasoning="ok",
                    criteria_scores={"accuracy": sc, "clarity": sc - 5},
                )

        runner = MockRunner()
        judge = VaryJudge()
        with (
            patch("pondera.api.load_case_yaml", return_value=multi_case),
            patch("pondera.api.get_settings"),
            patch("pondera.api.apply_prejudge_checks", return_value=[]),
            patch("pondera.api.choose_rubric", return_value=None),
            patch("pondera.api.compute_pass", return_value=True),
        ):
            result = await evaluate_case_async("/fake/path.yaml", runner=runner, judge=judge)
            assert isinstance(result, MultiEvaluationResult)
            assert len(result.evaluations) == 3
            overall_mean = result.aggregates.overall.mean
            assert overall_mean == pytest.approx(sum(scores) / len(scores))
            assert set(result.aggregates.per_criterion.keys()) == {"accuracy", "clarity"}

    @pytest.mark.asyncio
    async def test_evaluate_case_async_primary_metric_max(self, sample_case: CaseSpec) -> None:
        multi_case = CaseSpec(
            id=sample_case.id,
            input=sample_case.input,
            judge=CaseJudge(overall_threshold=80),
            repetitions=2,
        )
        scores = [60, 90]

        class VaryJudge(MockJudge):
            def __init__(self) -> None:
                self.idx = 0

            async def judge(self, **kwargs: Any) -> Judgment:
                sc = scores[self.idx]
                self.idx += 1
                return Judgment(
                    score=sc,
                    evaluation_passed=True,
                    reasoning="ok",
                    criteria_scores={"accuracy": sc},
                )

        runner = MockRunner()
        judge = VaryJudge()
        with (
            patch("pondera.api.load_case_yaml", return_value=multi_case),
            patch("pondera.api.get_settings"),
            patch("pondera.api.apply_prejudge_checks", return_value=[]),
            patch("pondera.api.choose_rubric", return_value=None),
            patch("pondera.api.compute_pass", return_value=True),
        ):
            result = await evaluate_case_async(
                "/fake/path.yaml",
                runner=runner,
                judge=judge,
                primary_metric=AggregationMetric.max,
            )
            assert isinstance(result, MultiEvaluationResult)
            assert result.passed is True
            assert result.primary_metric == AggregationMetric.max


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

        assert isinstance(result, MultiEvaluationResult)
        assert len(result.evaluations) == 1
        single = result.evaluations[0]
        assert single.case_id == "test-case"
        assert runner.call_count == 1
        assert judge.call_count == 1

    @pytest.mark.asyncio
    async def test_evaluate_case_async_invalid_threshold_keys(
        self, sample_case: CaseSpec, sample_rubric: list[RubricCriterion]
    ) -> None:
        # Provide a threshold key not present in rubric or criteria_scores
        bad_case = CaseSpec(
            id="test-case",
            input=sample_case.input,
            judge=CaseJudge(
                request="Judge",
                rubric=sample_rubric,
                overall_threshold=50,
                per_criterion_thresholds={"nonexistent": 10},
            ),
        )
        runner = MockRunner()
        # Judge returns criteria without the bad key
        judge = MockJudge(
            judgment=Judgment(
                score=80,
                evaluation_passed=True,
                reasoning="ok",
                criteria_scores={"accuracy": 80, "clarity": 75},
            )
        )
        with (
            patch("pondera.api.load_case_yaml", return_value=bad_case),
            patch("pondera.api.get_settings"),
            patch("pondera.api.apply_prejudge_checks", return_value=[]),
            patch("pondera.api.choose_rubric", return_value=sample_rubric),
        ):
            # Fail-fast now surfaces as structured ValidationError from compute_pass
            with pytest.raises(
                ValidationError, match="Missing criterion score for threshold key 'nonexistent'"
            ):
                await evaluate_case_async("/fake/path.yaml", runner=runner, judge=judge)

    def test_evaluate_case_default_judge(self, sample_case: CaseSpec) -> None:
        """If no judge passed, built-in Judge should be instantiated and used."""
        runner = MockRunner()
        with (
            patch("pondera.api.load_case_yaml", return_value=sample_case),
            patch("pondera.api.get_settings"),
            patch("pondera.api.apply_prejudge_checks", return_value=[]),
            patch("pondera.api.choose_rubric", return_value=None),
            patch("pondera.api.compute_pass", return_value=True),
            patch("pondera.api.Judge") as mock_builtin_judge,
        ):
            inst = mock_builtin_judge.return_value

            # Provide an async mock for judge method
            async def _mock_judge(**kwargs):  # type: ignore
                return Judgment(
                    score=90,
                    evaluation_passed=True,
                    reasoning="ok",
                    criteria_scores={"accuracy": 90},
                    issues=[],
                    suggestions=[],
                )

            inst.judge.side_effect = _mock_judge
            result = evaluate_case("/fake/path.yaml", runner=runner)
        assert isinstance(result, MultiEvaluationResult)
        assert len(result.evaluations) == 1
        single = result.evaluations[0]
        assert single.judgment.score == 90
        mock_builtin_judge.assert_called_once()

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

        assert isinstance(result, MultiEvaluationResult)
        assert len(result.evaluations) == 1
        single = result.evaluations[0]
        assert single.case_id == "test-case"

    def test_evaluate_case_multi_sync(self, sample_case: CaseSpec) -> None:
        """Sync wrapper returns MultiEvaluationResult when repetitions>1."""
        multi_case = CaseSpec(
            id=sample_case.id,
            input=sample_case.input,
            judge=sample_case.judge,
            repetitions=2,
        )
        runner = MockRunner()
        judge = MockJudge()
        with (
            patch("pondera.api.load_case_yaml", return_value=multi_case),
            patch("pondera.api.get_settings"),
            patch("pondera.api.apply_prejudge_checks", return_value=[]),
            patch("pondera.api.choose_rubric", return_value=None),
            patch("pondera.api.compute_pass", return_value=True),
        ):
            result = evaluate_case("/fake/path.yaml", runner=runner, judge=judge)
        assert isinstance(result, MultiEvaluationResult)
        assert len(result.evaluations) == 2


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
            answer="The capital of France is Paris.",
            artifacts=["source.txt"],
            metadata={"confidence": 0.95},
        )
        runner = MockRunner(result=run_result)

        # Create judge that returns specific judgment
        judgment = Judgment(
            score=92,  # Integer
            evaluation_passed=True,  # Required field
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
            assert isinstance(result, MultiEvaluationResult)
            assert len(result.evaluations) == 1
            single = result.evaluations[0]
            assert single.case_id == "test-case"
            assert single.case == sample_case
            assert single.run == run_result
            assert single.judgment == judgment
            assert single.precheck_failures == []
            assert single.overall_threshold == 7.0
            assert single.per_criterion_thresholds == {}  # Empty dict from fixture
            assert single.passed is True
            assert "runner_s" in single.timings_s
            assert "judge_s" in single.timings_s
            assert "total_s" in single.timings_s
