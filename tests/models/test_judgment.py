import pytest
from pydantic import ValidationError

from pondera.models.judgment import Judgment


class TestJudgment:
    """Tests for Judgment model."""

    def test_valid_judgment(self) -> None:
        """Test creating a valid judgment."""
        judgment = Judgment(
            score=85,
            pass_fail=True,
            reasoning="The answer is correct and well-explained.",
            criteria_scores={"correctness": 90, "completeness": 80},
        )

        assert judgment.score == 85
        assert judgment.pass_fail is True
        assert judgment.reasoning == "The answer is correct and well-explained."
        assert judgment.criteria_scores == {"correctness": 90, "completeness": 80}
        assert judgment.issues == []
        assert judgment.suggestions == []

    def test_judgment_with_optional_fields(self) -> None:
        """Test creating judgment with all optional fields."""
        judgment = Judgment(
            score=60,
            pass_fail=False,
            reasoning="The answer has some issues.",
            criteria_scores={"correctness": 70, "completeness": 50},
            issues=["Missing key information", "Incorrect calculation"],
            suggestions=["Add more details", "Check your math"],
        )

        assert judgment.score == 60
        assert judgment.pass_fail is False
        assert judgment.reasoning == "The answer has some issues."
        assert judgment.criteria_scores == {"correctness": 70, "completeness": 50}
        assert judgment.issues == ["Missing key information", "Incorrect calculation"]
        assert judgment.suggestions == ["Add more details", "Check your math"]

    def test_score_range_validation(self) -> None:
        """Test that score must be between 0 and 100."""
        with pytest.raises(ValidationError) as exc_info:
            Judgment(score=101, pass_fail=True, reasoning="test", criteria_scores={})

        assert "Input should be less than or equal to 100" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            Judgment(score=-1, pass_fail=True, reasoning="test", criteria_scores={})

        assert "Input should be greater than or equal to 0" in str(exc_info.value)

    def test_missing_required_fields(self) -> None:
        """Test that missing required fields raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Judgment()  # type: ignore

        error_str = str(exc_info.value)
        assert "Field required" in error_str

    def test_minimal_judgment(self) -> None:
        """Test creating judgment with minimal required fields."""
        judgment = Judgment(
            score=75, pass_fail=True, reasoning="Good answer", criteria_scores={"overall": 75}
        )

        assert judgment.score == 75
        assert judgment.pass_fail is True
        assert judgment.reasoning == "Good answer"
        assert judgment.criteria_scores == {"overall": 75}

    def test_empty_criteria_scores(self) -> None:
        """Test that empty criteria_scores is allowed."""
        judgment = Judgment(
            score=50, pass_fail=False, reasoning="No specific criteria", criteria_scores={}
        )

        assert judgment.criteria_scores == {}

    def test_extra_fields_forbidden(self) -> None:
        """Test that extra fields are forbidden."""
        with pytest.raises(ValidationError) as exc_info:
            Judgment(
                score=80,
                pass_fail=True,
                reasoning="test",
                criteria_scores={},
                extra_field="not allowed",  # type: ignore
            )

        assert "Extra inputs are not permitted" in str(exc_info.value)
