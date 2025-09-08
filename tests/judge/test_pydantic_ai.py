import pytest
from unittest.mock import Mock, patch, AsyncMock
from typing import Any

from pondera.judge.pydantic_ai import PydanticAIJudge
from pondera.judge.base import JudgeError
from pondera.models.rubric import RubricCriterion
from pondera.models.judgment import Judgment


class TestPydanticAIJudge:
    """Tests for PydanticAIJudge class."""

    @patch("pondera.judge.pydantic_ai.get_settings")
    @patch("pondera.judge.pydantic_ai.Agent")
    def test_init_with_defaults(self, mock_agent: Any, mock_get_settings: Any) -> None:
        """Test PydanticAIJudge initialization with default settings."""
        # Mock settings
        mock_settings = Mock()
        mock_settings.judge_model = "openai:gpt-4"
        mock_get_settings.return_value = mock_settings

        # Mock agent
        mock_agent_instance = Mock()
        mock_agent.return_value = mock_agent_instance

        PydanticAIJudge()

        # Verify settings were retrieved
        mock_get_settings.assert_called_once()

        # Verify agent was created with correct parameters
        mock_agent.assert_called_once()
        call_args = mock_agent.call_args
        assert call_args.kwargs["model"] == "openai:gpt-4"
        assert call_args.kwargs["result_type"] == Judgment
        assert "system_prompt" in call_args.kwargs

    @patch("pondera.judge.pydantic_ai.get_settings")
    @patch("pondera.judge.pydantic_ai.Agent")
    def test_init_with_custom_model(self, mock_agent: Any, mock_get_settings: Any) -> None:
        """Test PydanticAIJudge initialization with custom model."""
        mock_settings = Mock()
        mock_settings.judge_model = "openai:gpt-4"
        mock_get_settings.return_value = mock_settings

        mock_agent_instance = Mock()
        mock_agent.return_value = mock_agent_instance

        custom_model = "anthropic:claude-3-sonnet"
        PydanticAIJudge(model=custom_model)

        # Verify agent was created with custom model
        call_args = mock_agent.call_args
        assert call_args.kwargs["model"] == custom_model

    @patch("pondera.judge.pydantic_ai.get_settings")
    @patch("pondera.judge.pydantic_ai.Agent")
    def test_init_with_custom_rubric(self, mock_agent: Any, mock_get_settings: Any) -> None:
        """Test PydanticAIJudge initialization with custom rubric."""
        mock_settings = Mock()
        mock_settings.judge_model = "openai:gpt-4"
        mock_get_settings.return_value = mock_settings

        mock_agent_instance = Mock()
        mock_agent.return_value = mock_agent_instance

        custom_rubric = [RubricCriterion(name="accuracy", weight=1.0, description="How accurate")]

        PydanticAIJudge(rubric=custom_rubric)

        # Check that the system prompt includes the custom rubric
        call_args = mock_agent.call_args
        system_prompt = call_args.kwargs["system_prompt"]
        assert "accuracy" in system_prompt

    @patch("pondera.judge.pydantic_ai.get_settings")
    @patch("pondera.judge.pydantic_ai.Agent")
    def test_init_with_system_append(self, mock_agent: Any, mock_get_settings: Any) -> None:
        """Test PydanticAIJudge initialization with system append."""
        mock_settings = Mock()
        mock_settings.judge_model = "openai:gpt-4"
        mock_get_settings.return_value = mock_settings

        mock_agent_instance = Mock()
        mock_agent.return_value = mock_agent_instance

        system_append = "Be extra strict about formatting."
        PydanticAIJudge(system_append=system_append)

        # Check that system append is included in system prompt
        call_args = mock_agent.call_args
        system_prompt = call_args.kwargs["system_prompt"]
        assert system_append in system_prompt

    @patch("pondera.judge.pydantic_ai.get_settings")
    @patch("pondera.judge.pydantic_ai.Agent")
    @pytest.mark.asyncio
    async def test_judge_with_defaults(self, mock_agent: Any, mock_get_settings: Any) -> None:
        """Test judge method with default parameters."""
        # Setup mocks
        mock_settings = Mock()
        mock_settings.judge_model = "openai:gpt-4"
        mock_get_settings.return_value = mock_settings

        mock_result = Mock()
        mock_result.data = Judgment(
            score=85, pass_fail=True, reasoning="Good answer", criteria_scores={"correctness": 85}
        )

        mock_agent_instance = Mock()
        mock_agent_instance.run = AsyncMock(return_value=mock_result)
        mock_agent_instance.system_prompt = "default system prompt"
        mock_agent.return_value = mock_agent_instance

        judge = PydanticAIJudge()

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

        # Verify agent.run was called
        mock_agent_instance.run.assert_called_once()

    @patch("pondera.judge.pydantic_ai.get_settings")
    @patch("pondera.judge.pydantic_ai.Agent")
    @pytest.mark.asyncio
    async def test_judge_with_custom_model(self, mock_agent: Any, mock_get_settings: Any) -> None:
        """Test judge method with custom model override."""
        mock_settings = Mock()
        mock_settings.judge_model = "openai:gpt-4"
        mock_get_settings.return_value = mock_settings

        mock_result = Mock()
        mock_result.data = Judgment(
            score=90, pass_fail=True, reasoning="Excellent", criteria_scores={"correctness": 90}
        )

        # First call for initialization
        mock_agent_instance_init = Mock()
        mock_agent_instance_init.system_prompt = "init prompt"

        # Second call for custom model
        mock_agent_instance_custom = Mock()
        mock_agent_instance_custom.run = AsyncMock(return_value=mock_result)

        mock_agent.side_effect = [mock_agent_instance_init, mock_agent_instance_custom]

        judge = PydanticAIJudge()

        # Call with custom model
        result = await judge.judge(
            question="What is 2+2?",
            answer_markdown="2+2 = 4",
            judge_request="Check if correct",
            model="anthropic:claude-3-sonnet",
        )

        assert result.score == 90

        # Verify Agent was called twice (init + custom)
        assert mock_agent.call_count == 2

        # Check that the second call used the custom model
        second_call_args = mock_agent.call_args_list[1]
        assert second_call_args.kwargs["model"] == "anthropic:claude-3-sonnet"

    @patch("pondera.judge.pydantic_ai.get_settings")
    @patch("pondera.judge.pydantic_ai.Agent")
    @pytest.mark.asyncio
    async def test_judge_no_rubric_error(self, mock_agent: Any, mock_get_settings: Any) -> None:
        """Test that judge raises error when no rubric is provided."""
        mock_settings = Mock()
        mock_settings.judge_model = "openai:gpt-4"
        mock_get_settings.return_value = mock_settings

        mock_agent_instance = Mock()
        mock_agent_instance.run = AsyncMock()
        mock_agent.return_value = mock_agent_instance

        # Create judge with None as default rubric (simulating no default rubric)
        with patch("pondera.judge.pydantic_ai.default_rubric", return_value=[]):
            judge = PydanticAIJudge()

            with pytest.raises(JudgeError) as exc_info:
                await judge.judge(
                    question="Test",
                    answer_markdown="Test answer",
                    judge_request="Test request",
                    rubric=None,  # No override rubric provided
                )

            assert "No rubric provided" in str(exc_info.value)

    @patch("pondera.judge.pydantic_ai.get_settings")
    @patch("pondera.judge.pydantic_ai.Agent")
    @pytest.mark.asyncio
    async def test_judge_with_rubric_override(
        self, mock_agent: Any, mock_get_settings: Any
    ) -> None:
        """Test judge method with rubric override."""
        mock_settings = Mock()
        mock_settings.judge_model = "openai:gpt-4"
        mock_get_settings.return_value = mock_settings

        mock_result = Mock()
        mock_result.data = Judgment(
            score=75,
            pass_fail=True,
            reasoning="Meets custom criteria",
            criteria_scores={"custom_criterion": 75},
        )

        mock_agent_instance = Mock()
        mock_agent_instance.run = AsyncMock(return_value=mock_result)
        mock_agent.return_value = mock_agent_instance

        judge = PydanticAIJudge()

        custom_rubric = [
            RubricCriterion(
                name="custom_criterion", weight=1.0, description="Custom evaluation criterion"
            )
        ]

        result = await judge.judge(
            question="Test question",
            answer_markdown="Test answer",
            judge_request="Evaluate according to custom rubric",
            rubric=custom_rubric,
        )

        assert result.score == 75
        assert "custom_criterion" in result.criteria_scores

    def test_system_prompt_generation(self) -> None:
        """Test that system prompt is generated correctly."""
        with (
            patch("pondera.judge.pydantic_ai.get_settings") as mock_get_settings,
            patch("pondera.judge.pydantic_ai.Agent") as mock_agent,
        ):
            mock_settings = Mock()
            mock_settings.judge_model = "openai:gpt-4"
            mock_get_settings.return_value = mock_settings

            mock_agent_instance = Mock()
            mock_agent.return_value = mock_agent_instance

            custom_rubric = [
                RubricCriterion(name="test_criterion", weight=1.0, description="Test description")
            ]

            PydanticAIJudge(rubric=custom_rubric, system_append="Extra instructions")

            # Get the system prompt from the Agent call
            call_args = mock_agent.call_args
            system_prompt = call_args.kwargs["system_prompt"]

            # Verify key components are in the system prompt
            assert "impartial evaluator" in system_prompt.lower()
            assert "test_criterion" in system_prompt
            assert "Test description" in system_prompt
            assert "Extra instructions" in system_prompt
            assert "JSON" in system_prompt
            assert "Judgment" in system_prompt
            assert "score" in system_prompt
            assert "pass_fail" in system_prompt
