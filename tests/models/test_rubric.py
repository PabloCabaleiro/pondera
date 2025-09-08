import pytest
from pydantic import ValidationError

from pondera.models.rubric import RubricCriterion, Rubric


class TestRubricCriterion:
    """Tests for RubricCriterion model."""

    def test_valid_criterion(self) -> None:
        """Test creating a valid rubric criterion."""
        criterion = RubricCriterion(
            name="correctness", weight=2.5, description="How correct is the answer?"
        )

        assert criterion.name == "correctness"
        assert criterion.weight == 2.5
        assert criterion.description == "How correct is the answer?"

    def test_empty_name_fails(self) -> None:
        """Test that empty name raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            RubricCriterion(name="", weight=1.0, description="test")

        assert "String should have at least 1 character" in str(exc_info.value)

    def test_empty_description_fails(self) -> None:
        """Test that empty description raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            RubricCriterion(name="test", weight=1.0, description="")

        assert "String should have at least 1 character" in str(exc_info.value)

    def test_zero_weight_fails(self) -> None:
        """Test that zero weight raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            RubricCriterion(name="test", weight=0.0, description="test")

        assert "Input should be greater than 0" in str(exc_info.value)

    def test_negative_weight_fails(self) -> None:
        """Test that negative weight raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            RubricCriterion(name="test", weight=-1.0, description="test")

        assert "Input should be greater than 0" in str(exc_info.value)

    def test_missing_required_fields(self) -> None:
        """Test that missing required fields raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            RubricCriterion()  # type: ignore

        error_str = str(exc_info.value)
        assert "Field required" in error_str

    def test_extra_fields_forbidden(self) -> None:
        """Test that extra fields are forbidden."""
        with pytest.raises(ValidationError) as exc_info:
            RubricCriterion(
                name="test",
                weight=1.0,
                description="test",
                extra_field="not allowed",  # type: ignore
            )

        assert "Extra inputs are not permitted" in str(exc_info.value)


class TestRubric:
    """Tests for Rubric model."""

    def test_valid_rubric(self) -> None:
        """Test creating a valid rubric."""
        criteria = [
            RubricCriterion(name="correctness", weight=2.0, description="Correctness"),
            RubricCriterion(name="completeness", weight=1.5, description="Completeness"),
        ]
        rubric = Rubric(rubric=criteria)

        assert len(rubric.rubric) == 2
        assert rubric.rubric[0].name == "correctness"
        assert rubric.rubric[1].name == "completeness"

    def test_empty_rubric_fails(self) -> None:
        """Test that empty rubric raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Rubric(rubric=[])

        assert "rubric must contain at least one criterion" in str(exc_info.value)

    def test_total_weight_single_criterion(self) -> None:
        """Test total weight calculation with single criterion."""
        criterion = RubricCriterion(name="test", weight=3.5, description="test")
        rubric = Rubric(rubric=[criterion])

        assert rubric.total_weight() == 3.5

    def test_total_weight_multiple_criteria(self) -> None:
        """Test total weight calculation with multiple criteria."""
        criteria = [
            RubricCriterion(name="correctness", weight=2.0, description="Correctness"),
            RubricCriterion(name="completeness", weight=1.5, description="Completeness"),
            RubricCriterion(name="clarity", weight=1.0, description="Clarity"),
        ]
        rubric = Rubric(rubric=criteria)

        assert rubric.total_weight() == 4.5

    def test_extra_fields_forbidden(self) -> None:
        """Test that extra fields are forbidden."""
        criteria = [RubricCriterion(name="test", weight=1.0, description="test")]

        with pytest.raises(ValidationError) as exc_info:
            Rubric(rubric=criteria, extra_field="not allowed")  # type: ignore

        assert "Extra inputs are not permitted" in str(exc_info.value)
