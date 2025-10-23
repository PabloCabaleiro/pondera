import pytest
from pydantic import ValidationError

from pondera.models.case import CaseExpectations, CaseInput, CaseJudge, CaseSpec
from pondera.models.rubric import RubricCriterion


class TestCaseExpectations:
    """Tests for CaseExpectations model."""

    def test_default_expectations(self) -> None:
        """Test creating expectations with default values."""
        expectations = CaseExpectations()

        assert expectations.must_contain == []
        assert expectations.must_not_contain == []
        assert expectations.regex_must_match == []

    def test_populated_expectations(self) -> None:
        """Test creating expectations with values."""
        expectations = CaseExpectations(
            must_contain=["hello", "world"],
            must_not_contain=["error", "fail"],
            regex_must_match=[r"\d+", r"[A-Z]+"],
        )

        assert expectations.must_contain == ["hello", "world"]
        assert expectations.must_not_contain == ["error", "fail"]
        assert expectations.regex_must_match == [r"\d+", r"[A-Z]+"]


class TestCaseInput:
    """Tests for CaseInput model."""

    def test_minimal_input(self) -> None:
        """Test creating input with minimal required fields."""
        case_input = CaseInput(query="What is 2+2?")

        assert case_input.query == "What is 2+2?"
        assert case_input.attachments == []
        assert case_input.params == {}

    def test_full_input(self) -> None:
        """Test creating input with all fields."""
        case_input = CaseInput(
            query="Analyze this file",
            attachments=["file1.txt", "file2.csv"],
            params={"temperature": 0.7, "max_tokens": 100},
        )

        assert case_input.query == "Analyze this file"
        assert case_input.attachments == ["file1.txt", "file2.csv"]
        assert case_input.params == {"temperature": 0.7, "max_tokens": 100}

    def test_empty_query_fails(self) -> None:
        """Test that empty query raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            CaseInput(query="")

        assert "String should have at least 1 character" in str(exc_info.value)

    def test_missing_query_fails(self) -> None:
        """Test that missing query raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            CaseInput()  # type: ignore

        assert "Field required" in str(exc_info.value)


class TestCaseJudge:
    """Tests for CaseJudge model."""

    def test_default_judge(self) -> None:
        """Test creating judge with default values."""
        judge = CaseJudge()

        assert "Judge for factual correctness" in judge.request
        assert judge.overall_threshold == 70
        assert judge.per_criterion_thresholds == {}
        assert judge.rubric is None
        assert judge.system_append == ""

    def test_full_judge(self) -> None:
        """Test creating judge with all fields."""
        rubric_criteria = [
            RubricCriterion(name="accuracy", weight=1.0, description="Accuracy test")
        ]

        judge = CaseJudge(
            request="Custom judge request",
            overall_threshold=85,
            per_criterion_thresholds={"accuracy": 90, "completeness": 80},
            rubric=rubric_criteria,
            system_append="Be extra strict",
        )

        assert judge.request == "Custom judge request"
        assert judge.overall_threshold == 85
        assert judge.per_criterion_thresholds == {"accuracy": 90, "completeness": 80}
        assert len(judge.rubric) == 1
        assert judge.rubric[0].name == "accuracy"
        assert judge.system_append == "Be extra strict"

    def test_invalid_threshold_range(self) -> None:
        """Test that threshold outside 0-100 range fails."""
        with pytest.raises(ValidationError) as exc_info:
            CaseJudge(overall_threshold=101)

        assert "Input should be less than or equal to 100" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            CaseJudge(overall_threshold=-1)

        assert "Input should be greater than or equal to 0" in str(exc_info.value)


class TestCaseSpec:
    """Tests for CaseSpec model."""

    def test_minimal_case_spec(self) -> None:
        """Test creating case spec with minimal required fields."""
        case_input = CaseInput(query="What is 2+2?")
        case_spec = CaseSpec(id="test-case", input=case_input)

        assert case_spec.id == "test-case"
        assert case_spec.input.query == "What is 2+2?"
        assert case_spec.expect.must_contain == []
        assert case_spec.judge.overall_threshold == 70
        assert case_spec.timeout_s == 240

    def test_full_case_spec(self) -> None:
        """Test creating case spec with all fields."""
        case_input = CaseInput(
            query="Analyze data", attachments=["data.csv"], params={"format": "json"}
        )
        expectations = CaseExpectations(
            must_contain=["analysis", "results"], must_not_contain=["error"]
        )
        judge = CaseJudge(overall_threshold=80, per_criterion_thresholds={"accuracy": 85})

        case_spec = CaseSpec(
            id="analysis-case", input=case_input, expect=expectations, judge=judge, timeout_s=300
        )

        assert case_spec.id == "analysis-case"
        assert case_spec.input.query == "Analyze data"
        assert case_spec.input.attachments == ["data.csv"]
        assert case_spec.expect.must_contain == ["analysis", "results"]
        assert case_spec.judge.overall_threshold == 80
        assert case_spec.timeout_s == 300

    def test_empty_id_fails(self) -> None:
        """Test that empty id raises ValidationError."""
        case_input = CaseInput(query="test")

        with pytest.raises(ValidationError) as exc_info:
            CaseSpec(id="", input=case_input)

        assert "String should have at least 1 character" in str(exc_info.value)

    def test_missing_required_fields(self) -> None:
        """Test that missing required fields raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            CaseSpec()  # type: ignore

        assert "Field required" in str(exc_info.value)

    def test_invalid_timeout(self) -> None:
        """Test that invalid timeout raises ValidationError."""
        case_input = CaseInput(query="test")

        with pytest.raises(ValidationError) as exc_info:
            CaseSpec(id="test", input=case_input, timeout_s=0)

        assert "Input should be greater than 0" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            CaseSpec(id="test", input=case_input, timeout_s=-10)

        assert "Input should be greater than 0" in str(exc_info.value)
