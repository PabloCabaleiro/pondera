import pytest
from unittest.mock import Mock, patch
from typing import Any

from pondera.judge.base import Judge, JudgeError
from pondera.models.rubric import RubricCriterion
from pondera.models.judgment import Judgment


class TestJudge:
    """Tests for Judge class."""

    def test_init_with_defaults(self) -> None:
        """Test Judge initialization with default settings."""

        judge = Judge()

        # Verify judge was initialized with correct defaults
        assert judge._default_rubric is not None
        assert judge._system_append == ""

    def test_init_with_custom_rubric(self) -> None:
        """Test Judge initialization with custom rubric."""

        custom_rubric = [RubricCriterion(name="accuracy", weight=1.0, description="How accurate")]

        judge = Judge(rubric=custom_rubric)

        # Check that the custom rubric is stored
        assert judge._default_rubric == custom_rubric

    def test_init_with_system_append(self) -> None:
        """Test Judge initialization with system append."""

        system_append = "Be extra strict about formatting."
        judge = Judge(system_append=system_append)

        # Check that system append is stored
        assert judge._system_append == system_append

    @patch("pondera.judge.base.get_agent")
    @patch("pondera.judge.base.run_agent")
    @pytest.mark.asyncio
    async def test_judge_with_defaults(self, mock_run_agent: Any, mock_get_agent: Any) -> None:
        """Test judge method with default parameters."""
        # Setup mocks
        mock_agent = Mock()
        mock_get_agent.return_value = mock_agent

        expected_judgment = Judgment(
            score=85, pass_fail=True, reasoning="Good answer", criteria_scores={"correctness": 85}
        )
        mock_run_agent.return_value = (expected_judgment, [])

        judge = Judge()

        # Call judge method
        result = await judge.judge(
            question="What is 2+2?",
            answer_markdown="2+2 = 4",
            files=[],
            judge_request="Check if the answer is correct",
        )

        # Verify result
        assert isinstance(result, Judgment)
        assert result.score == 85
        assert result.pass_fail is True
        assert result.reasoning == "Good answer"

        # Verify mocks were called
        mock_get_agent.assert_called_once()
        mock_run_agent.assert_called_once()

    @patch("pondera.judge.base.get_agent")
    @patch("pondera.judge.base.run_agent")
    @pytest.mark.asyncio
    async def test_judge_with_custom_model(self, mock_run_agent: Any, mock_get_agent: Any) -> None:
        mock_agent = Mock()
        mock_get_agent.return_value = mock_agent

        expected_judgment = Judgment(
            score=90, pass_fail=True, reasoning="Excellent", criteria_scores={"correctness": 90}
        )
        mock_run_agent.return_value = (expected_judgment, [])

        judge = Judge()

        # Call judge method (no model parameter in new implementation)
        result = await judge.judge(
            question="What is 2+2?",
            answer_markdown="2+2 = 4",
            files=[],
            judge_request="Check if the answer is correct",
        )

        # Verify result
        assert isinstance(result, Judgment)
        assert result.score == 90

    @patch("pondera.judge.base.get_agent")
    @patch("pondera.judge.base.run_agent")
    @pytest.mark.asyncio
    async def test_judge_raises_error_without_rubric(
        self, mock_run_agent: Any, mock_get_agent: Any
    ) -> None:
        """Test that judge raises error when no rubric is provided."""

        with patch("pondera.judge.base.default_rubric", return_value=[]):
            judge = Judge()

            with pytest.raises(JudgeError, match="No rubric provided or configured"):
                await judge.judge(
                    question="What is 2+2?",
                    answer_markdown="2+2 = 4",
                    files=[],
                    judge_request="Check if the answer is correct",
                )

    @patch("pondera.judge.base.get_agent")
    @patch("pondera.judge.base.run_agent")
    @pytest.mark.asyncio
    async def test_judge_with_custom_rubric(self, mock_run_agent: Any, mock_get_agent: Any) -> None:
        """Test judge method with custom rubric."""

        mock_agent = Mock()
        mock_get_agent.return_value = mock_agent

        expected_judgment = Judgment(
            score=75, pass_fail=True, reasoning="Good", criteria_scores={"accuracy": 75}
        )
        mock_run_agent.return_value = (expected_judgment, [])

        judge = Judge()

        custom_rubric = [RubricCriterion(name="accuracy", weight=1.0, description="How accurate")]

        result = await judge.judge(
            question="What is 2+2?",
            answer_markdown="2+2 = 4",
            files=[],
            judge_request="Check if the answer is correct",
            rubric=custom_rubric,
        )

        assert result.score == 75

    def test_system_prompt_generation(self) -> None:
        """Test that system prompt is generated correctly."""

        custom_rubric = [RubricCriterion(name="accuracy", weight=1.0, description="How accurate")]

        judge = Judge(rubric=custom_rubric, system_append="Extra instructions")

        system_prompt = judge._system_prompt(custom_rubric, "Extra instructions")

        # Check that the system prompt contains expected elements
        assert "accuracy" in system_prompt
        assert "Extra instructions" in system_prompt
        assert "Judgment" in system_prompt
        assert "0-100" in system_prompt
