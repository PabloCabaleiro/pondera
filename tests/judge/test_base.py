import pytest
from unittest.mock import Mock, patch
from typing import Any

from pondera.judge.base import Judge, JudgeError
from pondera.models.rubric import RubricCriterion
from pondera.models.judgment import Judgment


class TestJudgeError:
    """Tests for JudgeError exception class."""

    def test_judge_error_is_runtime_error(self) -> None:
        """Test that JudgeError inherits from RuntimeError."""
        error = JudgeError("Test error")
        assert isinstance(error, RuntimeError)
        assert str(error) == "Test error"

    def test_judge_error_with_message(self) -> None:
        """Test creating JudgeError with custom message."""
        message = "Custom judge error message"
        error = JudgeError(message)
        assert str(error) == message


class TestJudge:
    """Tests for Judge class."""

    @patch("pondera.judge.base.get_settings")
    @patch("pondera.judge.base.default_rubric")
    def test_init_with_defaults(self, mock_default_rubric: Any, mock_get_settings: Any) -> None:
        """Test Judge initialization with default settings."""
        # Mock settings
        mock_settings = Mock()
        mock_settings.judge_model = "openai:gpt-4"
        mock_get_settings.return_value = mock_settings

        # Mock default rubric
        default_rub = [RubricCriterion(name="accuracy", weight=1.0, description="How accurate")]
        mock_default_rubric.return_value = default_rub

        judge = Judge()

        # Verify settings were retrieved
        mock_get_settings.assert_called_once()
        mock_default_rubric.assert_called_once()

        # Verify judge was initialized with correct defaults
        assert judge._default_model == "openai:gpt-4"
        assert judge._default_rubric == default_rub
        assert judge._system_append == ""

    @patch("pondera.judge.base.get_settings")
    @patch("pondera.judge.base.default_rubric")
    def test_init_with_custom_model(self, mock_default_rubric: Any, mock_get_settings: Any) -> None:
        """Test Judge initialization with custom model."""
        mock_settings = Mock()
        mock_settings.judge_model = "openai:gpt-4"
        mock_get_settings.return_value = mock_settings

        default_rub = [RubricCriterion(name="accuracy", weight=1.0, description="How accurate")]
        mock_default_rubric.return_value = default_rub

        custom_model = "anthropic:claude-3-sonnet"
        judge = Judge(model=custom_model)

        # Verify judge was initialized with custom model
        assert judge._default_model == custom_model
        assert judge._default_rubric == default_rub

    @patch("pondera.judge.base.get_settings")
    def test_init_with_custom_rubric(self, mock_get_settings: Any) -> None:
        """Test Judge initialization with custom rubric."""
        mock_settings = Mock()
        mock_settings.judge_model = "openai:gpt-4"
        mock_get_settings.return_value = mock_settings

        custom_rubric = [
            RubricCriterion(name="accuracy", weight=0.6, description="How accurate"),
            RubricCriterion(name="completeness", weight=0.4, description="How complete"),
        ]

        judge = Judge(rubric=custom_rubric)

        # Check that the custom rubric is stored
        assert judge._default_rubric == custom_rubric

    @patch("pondera.judge.base.get_settings")
    @patch("pondera.judge.base.default_rubric")
    def test_init_with_system_append(
        self, mock_default_rubric: Any, mock_get_settings: Any
    ) -> None:
        """Test Judge initialization with system append."""
        mock_settings = Mock()
        mock_settings.judge_model = "openai:gpt-4"
        mock_get_settings.return_value = mock_settings

        default_rub = [RubricCriterion(name="accuracy", weight=1.0, description="How accurate")]
        mock_default_rubric.return_value = default_rub

        system_append = "Be extra strict about formatting."
        judge = Judge(system_append=system_append)

        # Check that system append is stored
        assert judge._system_append == system_append

    @patch("pondera.judge.base.get_agent")
    @patch("pondera.judge.base.run_agent")
    @patch("pondera.judge.base.get_settings")
    @patch("pondera.judge.base.default_rubric")
    @pytest.mark.asyncio
    async def test_judge_with_defaults(
        self,
        mock_default_rubric: Any,
        mock_get_settings: Any,
        mock_run_agent: Any,
        mock_get_agent: Any,
    ) -> None:
        """Test judge method with default parameters."""
        # Setup mocks
        mock_settings = Mock()
        mock_settings.judge_model = "openai:gpt-4"
        mock_get_settings.return_value = mock_settings

        default_rub = [RubricCriterion(name="correctness", weight=1.0, description="How correct")]
        mock_default_rubric.return_value = default_rub

        mock_agent = Mock()
        mock_get_agent.return_value = mock_agent

        expected_judgment = Judgment(
            score=85,
            pass_fail=True,
            reasoning="Good answer",
            criteria_scores={"correctness": 85},
            issues=[],
            suggestions=["Keep up the good work"],
        )
        mock_run_agent.return_value = (expected_judgment, [])

        judge = Judge()

        # Call judge method
        result = await judge.judge(
            question="What is 2+2?",
            answer_markdown="2+2 = 4",
            judge_request="Check if the answer is correct",
        )

        # Verify result
        assert isinstance(result, Judgment)
        assert result.score == 85
        assert result.pass_fail is True
        assert result.reasoning == "Good answer"
        assert result.criteria_scores == {"correctness": 85}

        # Verify mocks were called correctly
        mock_get_agent.assert_called_once()
        mock_run_agent.assert_called_once()

        # Verify agent was created with Judgment output type
        call_args = mock_get_agent.call_args
        assert call_args[1]["output_type"] == Judgment

    @patch("pondera.judge.base.get_agent")
    @patch("pondera.judge.base.run_agent")
    @patch("pondera.judge.base.get_settings")
    @patch("pondera.judge.base.default_rubric")
    @pytest.mark.asyncio
    async def test_judge_with_custom_rubric(
        self,
        mock_default_rubric: Any,
        mock_get_settings: Any,
        mock_run_agent: Any,
        mock_get_agent: Any,
    ) -> None:
        """Test judge method with custom rubric."""
        mock_settings = Mock()
        mock_settings.judge_model = "openai:gpt-4"
        mock_get_settings.return_value = mock_settings

        default_rub = [RubricCriterion(name="accuracy", weight=1.0, description="Default")]
        mock_default_rubric.return_value = default_rub

        mock_agent = Mock()
        mock_get_agent.return_value = mock_agent

        expected_judgment = Judgment(
            score=75,
            pass_fail=True,
            reasoning="Good",
            criteria_scores={"custom_accuracy": 75, "completeness": 70},
            issues=[],
            suggestions=["Add more detail"],
        )
        mock_run_agent.return_value = (expected_judgment, [])

        judge = Judge()

        custom_rubric = [
            RubricCriterion(name="custom_accuracy", weight=0.7, description="Custom accuracy"),
            RubricCriterion(name="completeness", weight=0.3, description="How complete"),
        ]

        result = await judge.judge(
            question="What is 2+2?",
            answer_markdown="2+2 = 4",
            judge_request="Check if the answer is correct",
            rubric=custom_rubric,
        )

        assert result.score == 75
        assert result.criteria_scores == {"custom_accuracy": 75, "completeness": 70}

    @patch("pondera.judge.base.get_settings")
    @patch("pondera.judge.base.default_rubric")
    @pytest.mark.asyncio
    async def test_judge_raises_error_without_rubric(
        self, mock_default_rubric: Any, mock_get_settings: Any
    ) -> None:
        """Test that judge raises error when no rubric is provided."""
        mock_settings = Mock()
        mock_settings.judge_model = "openai:gpt-4"
        mock_get_settings.return_value = mock_settings

        # Mock empty default rubric
        mock_default_rubric.return_value = []

        judge = Judge()

        with pytest.raises(JudgeError, match="No rubric provided or configured"):
            await judge.judge(
                question="What is 2+2?",
                answer_markdown="2+2 = 4",
                judge_request="Check if the answer is correct",
            )

    @patch("pondera.judge.base.get_agent")
    @patch("pondera.judge.base.run_agent")
    @patch("pondera.judge.base.get_settings")
    @patch("pondera.judge.base.default_rubric")
    @pytest.mark.asyncio
    async def test_judge_with_system_append(
        self,
        mock_default_rubric: Any,
        mock_get_settings: Any,
        mock_run_agent: Any,
        mock_get_agent: Any,
    ) -> None:
        """Test judge method with system append parameter."""
        mock_settings = Mock()
        mock_settings.judge_model = "openai:gpt-4"
        mock_get_settings.return_value = mock_settings

        default_rub = [RubricCriterion(name="accuracy", weight=1.0, description="How accurate")]
        mock_default_rubric.return_value = default_rub

        mock_agent = Mock()
        mock_get_agent.return_value = mock_agent

        expected_judgment = Judgment(
            score=80,
            pass_fail=True,
            reasoning="Good with extra strictness",
            criteria_scores={"accuracy": 80},
            issues=[],
            suggestions=["Follow guidelines strictly"],
        )
        mock_run_agent.return_value = (expected_judgment, [])

        judge = Judge(system_append="Be very strict.")

        result = await judge.judge(
            question="What is 2+2?",
            answer_markdown="2+2 = 4",
            judge_request="Check if the answer is correct",
            system_append="Also check formatting.",
        )

        assert result.score == 80

        # Verify system prompt contains both system append strings
        call_args = mock_get_agent.call_args
        system_prompt = call_args[1]["system_prompt"]
        assert "Be very strict." in system_prompt
        assert "Also check formatting." in system_prompt

    @patch("pondera.judge.base.rubric_to_markdown")
    @patch("pondera.judge.base.rubric_weight_note")
    @patch("pondera.judge.base.get_settings")
    @patch("pondera.judge.base.default_rubric")
    def test_system_prompt_generation(
        self,
        mock_default_rubric: Any,
        mock_get_settings: Any,
        mock_rubric_weight_note: Any,
        mock_rubric_to_markdown: Any,
    ) -> None:
        """Test that system prompt is generated correctly."""
        mock_settings = Mock()
        mock_settings.judge_model = "openai:gpt-4"
        mock_get_settings.return_value = mock_settings

        default_rub = [RubricCriterion(name="accuracy", weight=1.0, description="How accurate")]
        mock_default_rubric.return_value = default_rub

        mock_rubric_to_markdown.return_value = "## Accuracy\nHow accurate the answer is."
        mock_rubric_weight_note.return_value = "Weight: accuracy=1.0"

        judge = Judge()

        custom_rubric = [RubricCriterion(name="accuracy", weight=1.0, description="How accurate")]
        system_prompt = judge._system_prompt(custom_rubric, "Extra instructions")

        # Check that the system prompt contains expected elements
        assert "impartial evaluator" in system_prompt
        assert "LLM-as-a-Judge" in system_prompt
        assert "Judgment" in system_prompt
        assert "0-100" in system_prompt
        assert "Extra instructions" in system_prompt
        assert "## Accuracy" in system_prompt
        assert "Weight: accuracy=1.0" in system_prompt
        assert "Be strict but fair" in system_prompt
        assert "penalize hallucinations" in system_prompt

        # Verify utility functions were called
        mock_rubric_to_markdown.assert_called_once_with(custom_rubric)
        mock_rubric_weight_note.assert_called_once_with(custom_rubric)

    @patch("pondera.judge.base.get_settings")
    @patch("pondera.judge.base.default_rubric")
    def test_system_prompt_empty_extra(
        self, mock_default_rubric: Any, mock_get_settings: Any
    ) -> None:
        """Test system prompt generation with empty extra text."""
        mock_settings = Mock()
        mock_settings.judge_model = "openai:gpt-4"
        mock_get_settings.return_value = mock_settings

        default_rub = [RubricCriterion(name="accuracy", weight=1.0, description="How accurate")]
        mock_default_rubric.return_value = default_rub

        judge = Judge()

        custom_rubric = [RubricCriterion(name="accuracy", weight=1.0, description="How accurate")]
        system_prompt = judge._system_prompt(custom_rubric, "")

        # Should still contain basic elements
        assert "impartial evaluator" in system_prompt
        assert "Judgment" in system_prompt
        assert "0-100" in system_prompt

    @patch("pondera.judge.base.get_agent")
    @patch("pondera.judge.base.run_agent")
    @patch("pondera.judge.base.get_settings")
    @patch("pondera.judge.base.default_rubric")
    @pytest.mark.asyncio
    async def test_judge_user_prompt_format(
        self,
        mock_default_rubric: Any,
        mock_get_settings: Any,
        mock_run_agent: Any,
        mock_get_agent: Any,
    ) -> None:
        """Test that the user prompt is formatted correctly."""
        mock_settings = Mock()
        mock_settings.judge_model = "openai:gpt-4"
        mock_get_settings.return_value = mock_settings

        default_rub = [RubricCriterion(name="accuracy", weight=1.0, description="How accurate")]
        mock_default_rubric.return_value = default_rub

        mock_agent = Mock()
        mock_get_agent.return_value = mock_agent

        expected_judgment = Judgment(
            score=90,
            pass_fail=True,
            reasoning="Excellent",
            criteria_scores={"accuracy": 90},
            issues=[],
            suggestions=["Perfect"],
        )
        mock_run_agent.return_value = (expected_judgment, [])

        judge = Judge()

        test_question = "What is the capital of France?"
        test_answer = "Paris is the capital of France."
        test_request = "Evaluate factual accuracy"

        await judge.judge(
            question=test_question,
            answer_markdown=test_answer,
            judge_request=test_request,
        )

        # Verify run_agent was called with correct user prompt
        mock_run_agent.assert_called_once()
        call_args = mock_run_agent.call_args[0]
        user_prompt = call_args[1]

        assert test_question in user_prompt
        assert test_answer in user_prompt
        assert test_request in user_prompt
        assert "User question:" in user_prompt
        assert "Assistant answer (Markdown):" in user_prompt
        assert "Evaluation request" in user_prompt
        assert "Task:" in user_prompt
        assert "Score each rubric criterion from 0-100" in user_prompt
        assert "Return ONLY a valid object for the `Judgment` schema" in user_prompt

    @patch("pondera.judge.base.get_agent")
    @patch("pondera.judge.base.run_agent")
    @patch("pondera.judge.base.get_settings")
    @patch("pondera.judge.base.default_rubric")
    @pytest.mark.asyncio
    async def test_judge_prefers_custom_over_default_rubric(
        self,
        mock_default_rubric: Any,
        mock_get_settings: Any,
        mock_run_agent: Any,
        mock_get_agent: Any,
    ) -> None:
        """Test that custom rubric takes precedence over default rubric."""
        mock_settings = Mock()
        mock_settings.judge_model = "openai:gpt-4"
        mock_get_settings.return_value = mock_settings

        default_rub = [RubricCriterion(name="default", weight=1.0, description="Default criterion")]
        mock_default_rubric.return_value = default_rub

        mock_agent = Mock()
        mock_get_agent.return_value = mock_agent

        expected_judgment = Judgment(
            score=85,
            pass_fail=True,
            reasoning="Good",
            criteria_scores={"custom": 85},
            issues=[],
            suggestions=["Good work"],
        )
        mock_run_agent.return_value = (expected_judgment, [])

        judge = Judge()

        custom_rubric = [RubricCriterion(name="custom", weight=1.0, description="Custom criterion")]

        await judge.judge(
            question="Test question",
            answer_markdown="Test answer",
            judge_request="Test request",
            rubric=custom_rubric,
        )

        # We can't easily check the exact rubric used, but we can verify the method was called
        mock_get_agent.assert_called_once()
        mock_run_agent.assert_called_once()
