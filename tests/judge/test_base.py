from unittest.mock import Mock

from pondera.judge.base import (
    JudgeError,
    Judge,
    rubric_to_markdown,
    default_rubric,
    rubric_weight_note,
)
from pondera.models.rubric import RubricCriterion
from pondera.models.judgment import Judgment


class TestJudgeError:
    """Tests for JudgeError exception."""

    def test_judge_error_creation(self) -> None:
        """Test creating a JudgeError."""
        error = JudgeError("Test error message")
        assert isinstance(error, RuntimeError)
        assert str(error) == "Test error message"

    def test_judge_error_inheritance(self) -> None:
        """Test that JudgeError inherits from RuntimeError."""
        error = JudgeError("Test")
        assert isinstance(error, RuntimeError)
        assert isinstance(error, Exception)


class TestJudgeProtocol:
    """Tests for Judge protocol."""

    def test_judge_protocol_exists(self) -> None:
        """Test that Judge protocol can be used for type checking."""
        # Create a mock that implements the Judge protocol
        mock_judge = Mock(spec=Judge)
        mock_judge.judge.return_value = Judgment(
            score=85, pass_fail=True, reasoning="Good answer", criteria_scores={"correctness": 85}
        )

        # Check that the mock has the required method
        assert hasattr(mock_judge, "judge")
        assert callable(mock_judge.judge)


class TestRubricToMarkdown:
    """Tests for rubric_to_markdown function."""

    def test_empty_rubric(self) -> None:
        """Test markdown generation for empty rubric."""
        result = rubric_to_markdown([])
        assert result == ""

    def test_single_criterion(self) -> None:
        """Test markdown generation for single criterion."""
        criterion = RubricCriterion(
            name="correctness", weight=1.0, description="Answer is factually correct"
        )

        result = rubric_to_markdown([criterion])
        expected = "- **correctness** (w=1): Answer is factually correct"
        assert result == expected

    def test_multiple_criteria(self) -> None:
        """Test markdown generation for multiple criteria."""
        criteria = [
            RubricCriterion(
                name="correctness", weight=0.5, description="Answer is factually correct"
            ),
            RubricCriterion(name="completeness", weight=0.3, description="Answer is complete"),
            RubricCriterion(name="clarity", weight=0.2, description="Answer is clear"),
        ]

        result = rubric_to_markdown(criteria)
        lines = result.split("\n")

        assert len(lines) == 3
        assert "- **correctness** (w=0.5): Answer is factually correct" in lines
        assert "- **completeness** (w=0.3): Answer is complete" in lines
        assert "- **clarity** (w=0.2): Answer is clear" in lines

    def test_weight_formatting(self) -> None:
        """Test that weights are formatted correctly (no unnecessary decimals)."""
        criteria = [
            RubricCriterion(name="test1", weight=1.0, description="Test 1"),
            RubricCriterion(name="test2", weight=0.5, description="Test 2"),
            RubricCriterion(name="test3", weight=0.33333, description="Test 3"),
        ]

        result = rubric_to_markdown(criteria)
        lines = result.split("\n")

        # Check that 1.0 is formatted as "1" not "1.0"
        assert "(w=1):" in lines[0]
        assert "(w=0.5):" in lines[1]
        assert "(w=0.33333):" in lines[2]

    def test_special_characters_in_description(self) -> None:
        """Test handling of special characters in descriptions."""
        criterion = RubricCriterion(
            name="test", weight=1.0, description="Description with **bold**, *italic*, and `code`"
        )

        result = rubric_to_markdown([criterion])
        assert "Description with **bold**, *italic*, and `code`" in result


class TestDefaultRubric:
    """Tests for default_rubric function."""

    def test_default_rubric_structure(self) -> None:
        """Test that default rubric has expected structure."""
        rubric = default_rubric()

        assert isinstance(rubric, list)
        assert len(rubric) > 0

        for criterion in rubric:
            assert isinstance(criterion, RubricCriterion)
            assert criterion.name
            assert criterion.weight > 0
            assert criterion.description

    def test_default_rubric_criteria_names(self) -> None:
        """Test that default rubric contains expected criteria."""
        rubric = default_rubric()
        criterion_names = [c.name for c in rubric]

        expected_names = [
            "correctness",
            "completeness",
            "methodology_repro",
            "safety_compliance",
            "presentation",
        ]

        for name in expected_names:
            assert name in criterion_names

    def test_default_rubric_weights_positive(self) -> None:
        """Test that all default rubric weights are positive."""
        rubric = default_rubric()

        for criterion in rubric:
            assert criterion.weight > 0

    def test_default_rubric_total_weight(self) -> None:
        """Test that default rubric weights sum to 1.0."""
        rubric = default_rubric()
        total_weight = sum(c.weight for c in rubric)

        # Allow for small floating point differences
        assert abs(total_weight - 1.0) < 0.001

    def test_default_rubric_immutability(self) -> None:
        """Test that multiple calls return independent lists."""
        rubric1 = default_rubric()
        rubric2 = default_rubric()

        # Should be equal in content but different objects
        assert rubric1 == rubric2
        assert rubric1 is not rubric2


class TestRubricWeightNote:
    """Tests for rubric_weight_note function."""

    def test_weight_note_single_criterion(self) -> None:
        """Test weight note for single criterion."""
        criterion = RubricCriterion(name="test", weight=2.5, description="Test criterion")

        result = rubric_weight_note([criterion])
        assert "total weight 2.5" in result
        assert "normalize" in result.lower()

    def test_weight_note_multiple_criteria(self) -> None:
        """Test weight note for multiple criteria."""
        criteria = [
            RubricCriterion(name="test1", weight=1.5, description="Test 1"),
            RubricCriterion(name="test2", weight=0.5, description="Test 2"),
            RubricCriterion(name="test3", weight=1.0, description="Test 3"),
        ]

        result = rubric_weight_note(criteria)
        assert "total weight 3" in result  # Should format as "3" not "3.0"

    def test_weight_note_normalized_rubric(self) -> None:
        """Test weight note for normalized rubric (sum=1.0)."""
        criteria = [
            RubricCriterion(name="test1", weight=0.6, description="Test 1"),
            RubricCriterion(name="test2", weight=0.4, description="Test 2"),
        ]

        result = rubric_weight_note(criteria)
        assert "total weight 1" in result

    def test_weight_note_empty_rubric(self) -> None:
        """Test weight note for empty rubric."""
        result = rubric_weight_note([])
        assert "total weight 0" in result

    def test_weight_note_formatting(self) -> None:
        """Test that weight note formats numbers correctly."""
        criteria = [
            RubricCriterion(name="test", weight=0.33333, description="Test"),
        ]

        result = rubric_weight_note(criteria)
        assert "0.33333" in result
