import pytest
from unittest.mock import Mock, patch
from typing import Any

from pondera.judge.base import Judge, JudgeError
from pondera.models.rubric import RubricCriterion
from pondera.models.judgment import Judgment


@patch("pondera.judge.base.default_rubric")
def test_init_with_defaults(mock_default_rubric: Any) -> None:
    default_rub = [RubricCriterion(name="accuracy", weight=1.0, description="How accurate")]
    mock_default_rubric.return_value = default_rub
    judge = Judge()
    mock_default_rubric.assert_called_once()
    assert judge._default_rubric == default_rub
    assert judge._system_append == ""


def test_init_with_custom_rubric() -> None:
    custom_rubric = [RubricCriterion(name="accuracy", weight=1.0, description="How accurate")]
    judge = Judge(rubric=custom_rubric)
    assert judge._default_rubric == custom_rubric


@patch("pondera.judge.base.get_agent")
@patch("pondera.judge.base.run_agent")
@patch("pondera.judge.base.default_rubric")
@pytest.mark.asyncio
async def test_judge_with_defaults(
    mock_default_rubric: Any, mock_run_agent: Any, mock_get_agent: Any
) -> None:
    mock_default_rubric.return_value = [
        RubricCriterion(name="correctness", weight=1.0, description="How correct")
    ]
    mock_agent = Mock()
    mock_get_agent.return_value = mock_agent
    expected_judgment = Judgment(
        score=85,
        evaluation_passed=True,
        reasoning="Good answer",
        criteria_scores={"correctness": 85},
    )
    mock_run_agent.return_value = (expected_judgment, [])
    judge = Judge()
    result = await judge.judge(
        question="What is 2+2?",
        answer="2+2 = 4",
        files=[],
        judge_request="Check if the answer is correct",
    )
    assert result.evaluation_passed is True
    mock_get_agent.assert_called_once()
    mock_run_agent.assert_called_once()


@patch("pondera.judge.base.default_rubric")
@pytest.mark.asyncio
async def test_judge_raises_error_without_rubric(mock_default_rubric: Any) -> None:
    mock_default_rubric.return_value = []
    judge = Judge()
    with pytest.raises(JudgeError, match="No rubric provided or configured"):
        await judge.judge(
            question="What is 2+2?",
            answer="2+2 = 4",
            files=[],
            judge_request="Check if the answer is correct",
        )


@patch("pondera.judge.base.get_agent")
@patch("pondera.judge.base.run_agent")
@patch("pondera.judge.base.default_rubric")
@pytest.mark.asyncio
async def test_judge_user_prompt_format(
    mock_default_rubric: Any, mock_run_agent: Any, mock_get_agent: Any
) -> None:
    mock_default_rubric.return_value = [
        RubricCriterion(name="accuracy", weight=1.0, description="How accurate")
    ]
    mock_agent = Mock()
    mock_get_agent.return_value = mock_agent
    expected_judgment = Judgment(
        score=90, evaluation_passed=True, reasoning="Excellent", criteria_scores={"accuracy": 90}
    )
    mock_run_agent.return_value = (expected_judgment, [])
    judge = Judge()
    await judge.judge(
        question="What is the capital of France?",
        answer="Paris is the capital of France.",
        files=[],
        judge_request="Evaluate factual accuracy",
    )
    mock_run_agent.assert_called_once()
