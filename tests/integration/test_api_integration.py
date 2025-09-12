"""Integration tests for the pondera API."""

from __future__ import annotations

import pytest
from pathlib import Path
from unittest.mock import patch, AsyncMock

from pondera.api import evaluate_case_async, evaluate_case
from pondera.models.multi_evaluation import MultiEvaluationResult
from pondera.judge.base import Judge
from tests.integration.test_runner import TestRunner, MathTestRunner


@pytest.mark.integration
class TestAPIIntegration:
    """Integration tests for the pondera API functions."""

    def test_evaluate_case_sync_basic(self) -> None:
        """Test synchronous evaluation of a basic case."""
        case_path = Path(__file__).parent / "data" / "basic_integration.yaml"
        runner = TestRunner("Paris is the capital of France")

        # Mock the agent functions to avoid real API calls
        with (
            patch("pondera.judge.base.get_agent") as mock_get_agent,
            patch("pondera.judge.base.run_agent") as mock_run_agent,
        ):
            # Create mock agent
            mock_agent = AsyncMock()
            mock_get_agent.return_value = mock_agent

            # Mock the judgment result
            from pondera.models.judgment import Judgment

            mock_judgment = Judgment(
                score=90.0,
                pass_fail=True,
                reasoning="Correct answer about Paris",
                criteria_scores={"accuracy": 90.0},
                issues=[],
                suggestions=["Great answer!"],
            )
            mock_run_agent.return_value = (mock_judgment, [])

            judge = Judge()

            # Run the evaluation
            result = evaluate_case(case_yaml_path=case_path, runner=runner, judge=judge)
            assert isinstance(result, MultiEvaluationResult)
            assert len(result.evaluations) == 1
            ev = result.evaluations[0]
            assert ev.case_id == "integration_basic_test"
            assert result.passed is not None
            assert ev.run.question == "What is the capital of France?"
            assert ev.run.answer == "Paris is the capital of France"
            assert ev.judgment is not None
            assert 0.0 <= ev.judgment.score <= 100.0

    @pytest.mark.asyncio
    async def test_evaluate_case_async_basic(self) -> None:
        """Test asynchronous evaluation of a basic case."""
        case_path = Path(__file__).parent / "data" / "basic_integration.yaml"
        runner = TestRunner("Paris is the capital of France")

        with (
            patch("pondera.judge.base.get_agent") as mock_get_agent,
            patch("pondera.judge.base.run_agent") as mock_run_agent,
        ):
            mock_agent = AsyncMock()
            mock_get_agent.return_value = mock_agent
            from pondera.models.judgment import Judgment

            mock_judgment = Judgment(
                score=90.0,
                pass_fail=True,
                reasoning="Correct answer about Paris",
                criteria_scores={"accuracy": 90.0},
                issues=[],
                suggestions=["Great answer!"],
            )
            mock_run_agent.return_value = (mock_judgment, [])

            judge = Judge()
            result = await evaluate_case_async(case_yaml_path=case_path, runner=runner, judge=judge)
            assert isinstance(result, MultiEvaluationResult)
            assert len(result.evaluations) == 1
            ev = result.evaluations[0]
            assert ev.case_id == "integration_basic_test"
            assert result.passed is not None
            assert ev.run.question == "What is the capital of France?"
            assert ev.run.answer == "Paris is the capital of France"
            assert ev.judgment is not None

    @pytest.mark.asyncio
    async def test_evaluate_case_with_math_runner(self) -> None:
        """Test evaluation with the math test runner."""
        case_path = Path(__file__).parent / "data" / "math_test.yaml"
        runner = MathTestRunner()

        with (
            patch("pondera.judge.base.get_agent") as mock_get_agent,
            patch("pondera.judge.base.run_agent") as mock_run_agent,
        ):
            mock_agent = AsyncMock()
            mock_get_agent.return_value = mock_agent
            from pondera.models.judgment import Judgment

            mock_judgment = Judgment(
                score=95.0,
                pass_fail=True,
                reasoning="Correct mathematical answer",
                criteria_scores={"accuracy": 95.0},
                issues=[],
                suggestions=["Perfect math solution!"],
            )
            mock_run_agent.return_value = (mock_judgment, [])

            judge = Judge()
            result = await evaluate_case_async(case_yaml_path=case_path, runner=runner, judge=judge)
            assert isinstance(result, MultiEvaluationResult)
            assert len(result.evaluations) == 1
            ev = result.evaluations[0]
            assert ev.case_id == "integration_math_test"
            assert ev.run.question == "What is 2 + 2?"
            assert ev.run.answer == "4"
            assert ev.judgment is not None
            assert ev.judgment.score >= 80

    @pytest.mark.asyncio
    async def test_evaluate_case_with_rubric(self) -> None:
        """Test evaluation with a custom rubric."""
        case_path = Path(__file__).parent / "data" / "rubric_test.yaml"
        runner = TestRunner(
            "Photosynthesis is the process by which plants convert sunlight into energy using chlorophyll"
        )

        with (
            patch("pondera.judge.base.get_agent") as mock_get_agent,
            patch("pondera.judge.base.run_agent") as mock_run_agent,
        ):
            mock_agent = AsyncMock()
            mock_get_agent.return_value = mock_agent
            from pondera.models.judgment import Judgment

            mock_judgment = Judgment(
                score=85.0,
                pass_fail=True,
                reasoning="Good explanation of photosynthesis",
                criteria_scores={"accuracy": 90.0, "completeness": 80.0},
                issues=[],
                suggestions=["Add more detail about chloroplasts"],
            )
            mock_run_agent.return_value = (mock_judgment, [])

            judge = Judge()
            result = await evaluate_case_async(case_path, runner=runner, judge=judge)
            assert isinstance(result, MultiEvaluationResult)
            assert len(result.evaluations) == 1
            ev = result.evaluations[0]
            assert ev.case_id == "integration_rubric_test"
            assert ev.judgment is not None
            assert "accuracy" in ev.judgment.criteria_scores
            assert "completeness" in ev.judgment.criteria_scores
            assert 0.0 <= ev.judgment.criteria_scores["accuracy"] <= 100.0
            assert 0.0 <= ev.judgment.criteria_scores["completeness"] <= 100.0

    @pytest.mark.asyncio
    async def test_evaluate_case_with_progress_callback(self) -> None:
        """Test evaluation with a progress callback."""
        case_path = Path(__file__).parent / "data" / "basic_integration.yaml"
        runner = TestRunner("Paris")

        with (
            patch("pondera.judge.base.get_agent") as mock_get_agent,
            patch("pondera.judge.base.run_agent") as mock_run_agent,
        ):
            mock_agent = AsyncMock()
            mock_get_agent.return_value = mock_agent
            from pondera.models.judgment import Judgment

            mock_judgment = Judgment(
                score=75.0,
                pass_fail=True,
                reasoning="Simple but correct answer",
                criteria_scores={"accuracy": 75.0},
                issues=[],
                suggestions=["Provide more context"],
            )
            mock_run_agent.return_value = (mock_judgment, [])

            judge = Judge()
            progress_messages: list[str] = []

            async def progress_callback(message: str) -> None:
                progress_messages.append(message)

            result = await evaluate_case_async(
                case_path, runner=runner, judge=judge, progress=progress_callback
            )
            assert isinstance(result, MultiEvaluationResult)
            assert len(result.evaluations) == 1
            ev = result.evaluations[0]
            assert len(progress_messages) > 0
            assert any("running case" in msg for msg in progress_messages)
            assert ev.case_id == "integration_basic_test"

    @pytest.mark.asyncio
    async def test_evaluate_case_failure_case(self) -> None:
        """Test evaluation that should fail the threshold."""
        case_path = Path(__file__).parent / "data" / "math_test.yaml"  # Expects "4"
        runner = TestRunner("Wrong answer: 5")

        with (
            patch("pondera.judge.base.get_agent") as mock_get_agent,
            patch("pondera.judge.base.run_agent") as mock_run_agent,
        ):
            mock_agent = AsyncMock()
            mock_get_agent.return_value = mock_agent
            from pondera.models.judgment import Judgment

            mock_judgment = Judgment(
                score=20.0,
                pass_fail=False,
                reasoning="Incorrect mathematical answer",
                criteria_scores={"accuracy": 20.0},
                issues=["Wrong calculation"],
                suggestions=["Check basic arithmetic"],
            )
            mock_run_agent.return_value = (mock_judgment, [])

            judge = Judge()
            result = await evaluate_case_async(case_path, runner=runner, judge=judge)
            assert isinstance(result, MultiEvaluationResult)
            assert len(result.evaluations) == 1
            ev = result.evaluations[0]
            assert ev.case_id == "integration_math_test"
            assert ev.run.answer == "Wrong answer: 5"
            assert ev.judgment is not None
            assert ev.judgment.score < 90
            assert result.passed is False
            assert ev.passed is False

    def test_evaluate_case_with_nonexistent_file(self) -> None:
        """Test evaluation with non-existent case file."""
        case_path = Path("/nonexistent/file.yaml")
        runner = TestRunner()
        judge = Judge()

        with pytest.raises(FileNotFoundError):
            evaluate_case(case_yaml_path=case_path, runner=runner, judge=judge)
