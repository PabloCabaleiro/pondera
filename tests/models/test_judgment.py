import pytest
from pydantic import ValidationError

from pondera.models.judgment import Judgment


class TestJudgment:
    """Tests for Judgment model."""

    def test_valid_judgment(self) -> None:
        judgment = Judgment(
            score=85,
            evaluation_passed=True,
            reasoning="The answer is correct and well-explained.",
            criteria_scores={"correctness": 90, "completeness": 80},
        )
        assert judgment.score == 85
        assert judgment.evaluation_passed is True
        assert judgment.reasoning == "The answer is correct and well-explained."
        assert judgment.criteria_scores == {"correctness": 90, "completeness": 80}
        assert judgment.issues == []
        assert judgment.suggestions == []

    def test_judgment_with_optional_fields(self) -> None:
        judgment = Judgment(
            score=60,
            evaluation_passed=False,
            reasoning="The answer has some issues.",
            criteria_scores={"correctness": 70, "completeness": 50},
            issues=["Missing key information", "Incorrect calculation"],
            suggestions=["Add more details", "Check your math"],
        )
        assert judgment.score == 60
        assert judgment.evaluation_passed is False
        assert judgment.reasoning == "The answer has some issues."
        assert judgment.criteria_scores == {"correctness": 70, "completeness": 50}
        assert judgment.issues == ["Missing key information", "Incorrect calculation"]
        assert judgment.suggestions == ["Add more details", "Check your math"]

    def test_score_range_validation(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            Judgment(score=101, evaluation_passed=True, reasoning="test", criteria_scores={})
        assert "less than or equal to 100" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            Judgment(score=-1, evaluation_passed=True, reasoning="test", criteria_scores={})
        assert "greater than or equal to 0" in str(exc_info.value)

    def test_missing_required_fields(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            Judgment()  # intentionally missing required fields
        assert "Field required" in str(exc_info.value)

    def test_minimal_judgment(self) -> None:
        judgment = Judgment(
            score=75,
            evaluation_passed=True,
            reasoning="Good answer",
            criteria_scores={"overall": 75},
        )
        assert judgment.score == 75
        assert judgment.evaluation_passed is True
        assert judgment.reasoning == "Good answer"
        assert judgment.criteria_scores == {"overall": 75}

    def test_empty_criteria_scores(self) -> None:
        judgment = Judgment(
            score=50, evaluation_passed=False, reasoning="No specific criteria", criteria_scores={}
        )
        assert judgment.criteria_scores == {}

    def test_extra_fields_forbidden(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            Judgment(
                score=80,
                evaluation_passed=True,
                reasoning="test",
                criteria_scores={},
                extra_field="not allowed",  # extra field to trigger validation error
            )
        assert "Extra inputs are not permitted" in str(exc_info.value)
