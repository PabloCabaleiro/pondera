"""Tests for pondera.utils module."""

import tempfile
from pathlib import Path

import pytest

from pondera.utils import load_case_yaml, apply_prejudge_checks, compute_pass, choose_rubric
from pondera.models.case import CaseSpec, CaseInput, CaseJudge, CaseExpectations
from pondera.models.rubric import RubricCriterion


class TestLoadCaseYaml:
    """Test the load_case_yaml function."""

    def test_loads_basic_case(self) -> None:
        """Test loading a basic case YAML file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            case_file = Path(tmpdir) / "test_case.yaml"
            yaml_content = """
id: test-case
input:
  query: "What is the capital of France?"
  attachments: []
  params: {}
judge:
  request: "Judge the accuracy of this answer"
  overall_threshold: 70
expect:
  must_contain: []
  must_not_contain: []
  regex_must_match: []
timeout_s: 120
"""
            case_file.write_text(yaml_content)

            case = load_case_yaml(case_file)

            assert case is not None
            assert case.id == "test-case"
            assert case.input.query == "What is the capital of France?"
            assert case.judge.request == "Judge the accuracy of this answer"
            assert case.judge.overall_threshold == 70
            assert case.timeout_s == 120

    def test_loads_with_string_path(self) -> None:
        """Test loading with string path instead of Path object."""
        with tempfile.TemporaryDirectory() as tmpdir:
            case_file = Path(tmpdir) / "test_case.yaml"
            yaml_content = """
id: string-path-test
input:
  query: "Test with string path"
judge:
  request: "Judge this"
"""
            case_file.write_text(yaml_content)

            # Use string path instead of Path object
            case = load_case_yaml(str(case_file))

            assert case.id == "string-path-test"
            assert case.input.query == "Test with string path"

    def test_loads_complex_case(self) -> None:
        """Test loading a case with all fields populated."""
        with tempfile.TemporaryDirectory() as tmpdir:
            case_file = Path(tmpdir) / "complex_case.yaml"
            yaml_content = """
id: complex-case
input:
  query: "Solve this complex problem"
  attachments: ["file1.txt", "file2.pdf"]
  params:
    temperature: 0.7
    max_tokens: 1000
judge:
  request: "Evaluate the solution thoroughly"
  overall_threshold: 85
  per_criterion_thresholds:
    accuracy: 90
    clarity: 80
  system_append: "Be thorough in your evaluation"
  rubric:
    - name: "accuracy"
      description: "How accurate is the answer"
      weight: 0.6
    - name: "clarity"
      description: "How clear is the explanation"
      weight: 0.4
expect:
  must_contain: ["solution", "answer"]
  must_not_contain: ["error", "fail"]
  regex_must_match: ["\\\\d+", "[Tt]he answer is"]
timeout_s: 300
"""
            case_file.write_text(yaml_content)

            case = load_case_yaml(case_file)

            assert case.id == "complex-case"
            assert case.input.query == "Solve this complex problem"
            assert case.input.attachments == ["file1.txt", "file2.pdf"]
            assert case.input.params == {"temperature": 0.7, "max_tokens": 1000}
            assert case.judge.overall_threshold == 85
            assert case.judge.per_criterion_thresholds == {"accuracy": 90, "clarity": 80}
            assert case.judge.system_append == "Be thorough in your evaluation"
            assert case.expect.must_contain == ["solution", "answer"]
            assert case.expect.must_not_contain == ["error", "fail"]
            assert case.expect.regex_must_match == ["\\d+", "[Tt]he answer is"]
            assert len(case.judge.rubric) == 2
            assert case.judge.rubric[0].name == "accuracy"
            assert case.judge.rubric[0].weight == 0.6
            assert case.timeout_s == 300

    def test_handles_missing_file(self) -> None:
        """Test error handling for missing file."""
        with pytest.raises(FileNotFoundError):
            load_case_yaml("/nonexistent/file.yaml")

    def test_handles_invalid_yaml(self) -> None:
        """Test error handling for invalid YAML syntax."""
        with tempfile.TemporaryDirectory() as tmpdir:
            case_file = Path(tmpdir) / "invalid.yaml"
            case_file.write_text("invalid: yaml: content: [")

            with pytest.raises(Exception):  # yaml.YAMLError or similar
                load_case_yaml(case_file)

    def test_handles_invalid_case_spec(self) -> None:
        """Test error handling for YAML that doesn't match CaseSpec."""
        with tempfile.TemporaryDirectory() as tmpdir:
            case_file = Path(tmpdir) / "invalid_spec.yaml"
            yaml_content = """
wrong_field: "this is not a valid CaseSpec"
missing_required_fields: true
"""
            case_file.write_text(yaml_content)

            with pytest.raises(Exception):  # Pydantic validation error
                load_case_yaml(case_file)


class TestApplyPrejudgeChecks:
    """Test the apply_prejudge_checks function."""

    def create_case_with_expectations(
        self,
        must_contain: list[str] | None = None,
        must_not_contain: list[str] | None = None,
        regex_must_match: list[str] | None = None,
    ) -> CaseSpec:
        """Helper to create a case with specific expectations."""
        return CaseSpec(
            id="test-case",
            input=CaseInput(query="test"),
            judge=CaseJudge(),
            expect=CaseExpectations(
                must_contain=must_contain or [],
                must_not_contain=must_not_contain or [],
                regex_must_match=regex_must_match or [],
            ),
        )

    def test_no_expectations_passes(self) -> None:
        """Test that answer passes when no expectations are set."""
        case = self.create_case_with_expectations()
        answer = "Any answer content here"

        failures = apply_prejudge_checks(answer, case)

        assert failures == []

    def test_must_contain_success(self) -> None:
        """Test successful must_contain checks."""
        case = self.create_case_with_expectations(must_contain=["Paris", "capital", "France"])
        answer = "The capital of France is Paris."

        failures = apply_prejudge_checks(answer, case)

        assert failures == []

    def test_must_contain_failure(self) -> None:
        """Test failed must_contain checks."""
        case = self.create_case_with_expectations(must_contain=["Paris", "capital", "missing_word"])
        answer = "The capital of France is Paris."

        failures = apply_prejudge_checks(answer, case)

        assert len(failures) == 1
        assert "must_contain failed: 'missing_word'" in failures[0]

    def test_must_contain_case_insensitive(self) -> None:
        """Test that must_contain checks are case-insensitive."""
        case = self.create_case_with_expectations(must_contain=["PARIS", "Capital"])
        answer = "The capital of France is paris."

        failures = apply_prejudge_checks(answer, case)

        assert failures == []

    def test_must_not_contain_success(self) -> None:
        """Test successful must_not_contain checks."""
        case = self.create_case_with_expectations(must_not_contain=["Berlin", "Germany", "wrong"])
        answer = "The capital of France is Paris."

        failures = apply_prejudge_checks(answer, case)

        assert failures == []

    def test_must_not_contain_failure(self) -> None:
        """Test failed must_not_contain checks."""
        case = self.create_case_with_expectations(must_not_contain=["Berlin", "Paris"])
        answer = "The capital of France is Paris, not Berlin."

        failures = apply_prejudge_checks(answer, case)

        assert len(failures) == 2  # Both Berlin and Paris should fail
        assert "must_not_contain failed: 'Berlin'" in failures
        assert "must_not_contain failed: 'Paris'" in failures

    def test_must_not_contain_case_insensitive(self) -> None:
        """Test that must_not_contain checks are case-insensitive."""
        case = self.create_case_with_expectations(must_not_contain=["WRONG"])
        answer = "This is the wrong answer."

        failures = apply_prejudge_checks(answer, case)

        assert len(failures) == 1
        assert "must_not_contain failed: 'WRONG'" in failures[0]

    def test_regex_must_match_success(self) -> None:
        """Test successful regex_must_match checks."""
        case = self.create_case_with_expectations(
            regex_must_match=[r"\d+", r"[Pp]aris", r"capital.+France"]
        )
        answer = "The capital of France is Paris. Population: 2,161,000."

        failures = apply_prejudge_checks(answer, case)

        assert failures == []

    def test_regex_must_match_failure(self) -> None:
        """Test failed regex_must_match checks."""
        case = self.create_case_with_expectations(regex_must_match=[r"\d+", r"[Pp]aris", r"Berlin"])
        answer = "The capital of France is Paris."

        failures = apply_prejudge_checks(answer, case)

        assert len(failures) == 2
        failure_patterns = [f.split(": ")[1].strip("'") for f in failures]
        assert r"\\d+" in failure_patterns
        assert r"Berlin" in failure_patterns

    def test_regex_case_insensitive(self) -> None:
        """Test that regex matching is case-insensitive."""
        case = self.create_case_with_expectations(regex_must_match=[r"PARIS", r"france"])
        answer = "The capital of France is Paris."

        failures = apply_prejudge_checks(answer, case)

        assert failures == []

    def test_regex_multiline(self) -> None:
        """Test that regex matching works across multiple lines."""
        case = self.create_case_with_expectations(regex_must_match=[r"^Answer:", r"conclusion$"])
        answer = """Answer: The capital is Paris.
Some explanation here.
This is my conclusion"""

        failures = apply_prejudge_checks(answer, case)

        assert failures == []

    def test_combined_checks(self) -> None:
        """Test multiple types of checks together."""
        case = self.create_case_with_expectations(
            must_contain=["Paris"], must_not_contain=["Berlin"], regex_must_match=[r"\d+"]
        )
        answer = "The capital of France is Paris. Population: 2161000."

        failures = apply_prejudge_checks(answer, case)

        assert failures == []

    def test_multiple_failures(self) -> None:
        """Test that multiple failures are all reported."""
        case = self.create_case_with_expectations(
            must_contain=["Paris", "missing1"],
            must_not_contain=["Berlin", "wrong"],
            regex_must_match=[r"\d+", r"missing_pattern"],
        )
        answer = "The answer is wrong and includes Berlin."

        failures = apply_prejudge_checks(answer, case)

        assert len(failures) == 6  # 2 must_contain + 2 must_not_contain + 2 regex failures

        failure_types = [f.split(" failed:")[0] for f in failures]
        assert failure_types.count("must_contain") == 2
        assert failure_types.count("must_not_contain") == 2
        assert failure_types.count("regex_must_match") == 2


class TestComputePass:
    """Test the compute_pass function."""

    def test_passes_when_all_criteria_met(self) -> None:
        """Test that result passes when all criteria are met."""
        result = compute_pass(
            precheck_failures=[],
            overall_threshold=70,
            per_criterion_thresholds={"accuracy": 80, "clarity": 75},
            criteria_scores={"accuracy": 85, "clarity": 80},
            overall_score=75,
        )

        assert result is True

    def test_fails_with_precheck_failures(self) -> None:
        """Test that result fails when precheck failures exist."""
        result = compute_pass(
            precheck_failures=["must_contain failed"],
            overall_threshold=70,
            per_criterion_thresholds={},
            criteria_scores={},
            overall_score=90,  # Even with high score
        )

        assert result is False

    def test_fails_below_overall_threshold(self) -> None:
        """Test that result fails when overall score is below threshold."""
        result = compute_pass(
            precheck_failures=[],
            overall_threshold=70,
            per_criterion_thresholds={},
            criteria_scores={},
            overall_score=65,
        )

        assert result is False

    def test_fails_below_criterion_threshold(self) -> None:
        """Test that result fails when any criterion is below threshold."""
        result = compute_pass(
            precheck_failures=[],
            overall_threshold=70,
            per_criterion_thresholds={"accuracy": 80, "clarity": 75},
            criteria_scores={"accuracy": 85, "clarity": 70},  # clarity below threshold
            overall_score=80,
        )

        assert result is False

    def test_passes_with_no_per_criterion_thresholds(self) -> None:
        """Test that result passes when no per-criterion thresholds are set."""
        result = compute_pass(
            precheck_failures=[],
            overall_threshold=70,
            per_criterion_thresholds=None,
            criteria_scores={"accuracy": 50, "clarity": 60},  # Low scores
            overall_score=75,
        )

        assert result is True

    def test_passes_with_empty_per_criterion_thresholds(self) -> None:
        """Test that result passes when per-criterion thresholds dict is empty."""
        result = compute_pass(
            precheck_failures=[],
            overall_threshold=70,
            per_criterion_thresholds={},
            criteria_scores={"accuracy": 50, "clarity": 60},
            overall_score=75,
        )

        assert result is True

    def test_handles_missing_criterion_score(self) -> None:
        """Test handling when a criterion score is missing (defaults to 0)."""
        result = compute_pass(
            precheck_failures=[],
            overall_threshold=70,
            per_criterion_thresholds={"accuracy": 80, "missing_criterion": 50},
            criteria_scores={"accuracy": 85},  # missing_criterion not provided
            overall_score=75,
        )

        # Should fail because missing_criterion defaults to 0, which is < 50
        assert result is False

    def test_passes_at_exact_thresholds(self) -> None:
        """Test that result passes when scores exactly meet thresholds."""
        result = compute_pass(
            precheck_failures=[],
            overall_threshold=70,
            per_criterion_thresholds={"accuracy": 80},
            criteria_scores={"accuracy": 80},  # Exactly at threshold
            overall_score=70,  # Exactly at threshold
        )

        assert result is True  # Should pass because scores >= threshold

    def test_passes_above_exact_thresholds(self) -> None:
        """Test that result passes when scores are above thresholds."""
        result = compute_pass(
            precheck_failures=[],
            overall_threshold=70,
            per_criterion_thresholds={"accuracy": 80},
            criteria_scores={"accuracy": 81},  # Above threshold
            overall_score=71,  # Above threshold
        )

        assert result is True

    def test_multiple_criterion_thresholds(self) -> None:
        """Test with multiple per-criterion thresholds."""
        result = compute_pass(
            precheck_failures=[],
            overall_threshold=70,
            per_criterion_thresholds={
                "accuracy": 80,
                "clarity": 75,
                "completeness": 70,
                "creativity": 85,
            },
            criteria_scores={"accuracy": 85, "clarity": 80, "completeness": 75, "creativity": 90},
            overall_score=80,
        )

        assert result is True


class TestChooseRubric:
    """Test the choose_rubric function."""

    def create_rubric_criterion(self, name: str, weight: float = 1.0) -> RubricCriterion:
        """Helper to create a rubric criterion."""
        return RubricCriterion(name=name, description=f"Description for {name}", weight=weight)

    def test_prefers_case_rubric(self) -> None:
        """Test that case rubric is preferred over default rubric."""
        case_rubric = [self.create_rubric_criterion("case_criterion")]
        default_rubric = [self.create_rubric_criterion("default_criterion")]

        result = choose_rubric(case_rubric, default_rubric)

        assert result == case_rubric
        assert result != default_rubric

    def test_uses_default_when_case_is_none(self) -> None:
        """Test that default rubric is used when case rubric is None."""
        case_rubric = None
        default_rubric = [self.create_rubric_criterion("default_criterion")]

        result = choose_rubric(case_rubric, default_rubric)

        assert result == default_rubric

    def test_uses_default_when_case_is_empty(self) -> None:
        """Test that default rubric is used when case rubric is empty list."""
        case_rubric: list[RubricCriterion] = []
        default_rubric = [self.create_rubric_criterion("default_criterion")]

        result = choose_rubric(case_rubric, default_rubric)

        assert result == default_rubric

    def test_returns_none_when_both_none(self) -> None:
        """Test that None is returned when both rubrics are None."""
        result = choose_rubric(None, None)

        assert result is None

    def test_returns_none_when_both_empty(self) -> None:
        """Test that empty list is returned when both rubrics are empty."""
        case_rubric: list[RubricCriterion] = []
        default_rubric: list[RubricCriterion] = []

        result = choose_rubric(case_rubric, default_rubric)

        assert result == []

    def test_case_rubric_overrides_even_when_default_none(self) -> None:
        """Test that case rubric is used even when default is None."""
        case_rubric = [self.create_rubric_criterion("case_criterion")]
        default_rubric = None

        result = choose_rubric(case_rubric, default_rubric)

        assert result == case_rubric

    def test_preserves_rubric_content(self) -> None:
        """Test that the chosen rubric content is preserved."""
        case_rubric = [
            self.create_rubric_criterion("accuracy", 0.6),
            self.create_rubric_criterion("clarity", 0.4),
        ]
        default_rubric = [self.create_rubric_criterion("default", 1.0)]

        result = choose_rubric(case_rubric, default_rubric)

        assert len(result) == 2
        assert result[0].name == "accuracy"
        assert result[0].weight == 0.6
        assert result[1].name == "clarity"
        assert result[1].weight == 0.4


class TestIntegration:
    """Integration tests combining multiple utils functions."""

    def test_full_case_processing_workflow(self) -> None:
        """Test a complete workflow from loading case to computing pass."""
        with tempfile.TemporaryDirectory() as tmpdir:
            case_file = Path(tmpdir) / "integration_test.yaml"
            yaml_content = """
id: integration-test
input:
  query: "What is 2 + 2?"
judge:
  request: "Evaluate the mathematical accuracy"
  overall_threshold: 70
  per_criterion_thresholds:
    accuracy: 80
  rubric:
    - name: "accuracy"
      description: "Mathematical correctness"
      weight: 1.0
expect:
  must_contain: ["4"]
  must_not_contain: ["wrong", "error"]
  regex_must_match: ["\\\\d+"]
"""
            case_file.write_text(yaml_content)

            # Load the case
            case = load_case_yaml(case_file)

            # Test a passing answer
            good_answer = "The answer is 4."
            precheck_failures = apply_prejudge_checks(good_answer, case)

            passing_result = compute_pass(
                precheck_failures=precheck_failures,
                overall_threshold=case.judge.overall_threshold,
                per_criterion_thresholds=case.judge.per_criterion_thresholds,
                criteria_scores={"accuracy": 90},
                overall_score=85,
            )

            assert precheck_failures == []
            assert passing_result is True

            # Test a failing answer
            bad_answer = "I don't know, this is wrong."
            precheck_failures = apply_prejudge_checks(bad_answer, case)

            failing_result = compute_pass(
                precheck_failures=precheck_failures,
                overall_threshold=case.judge.overall_threshold,
                per_criterion_thresholds=case.judge.per_criterion_thresholds,
                criteria_scores={"accuracy": 90},
                overall_score=85,
            )

            assert len(precheck_failures) > 0  # Should have precheck failures
            assert failing_result is False

    def test_rubric_selection_with_loaded_case(self) -> None:
        """Test rubric selection with a case loaded from YAML."""
        with tempfile.TemporaryDirectory() as tmpdir:
            case_file = Path(tmpdir) / "rubric_test.yaml"
            yaml_content = """
id: rubric-test
input:
  query: "Test question"
judge:
  request: "Judge this"
  rubric:
    - name: "custom_criterion"
      description: "Custom criterion from case"
      weight: 1.0
"""
            case_file.write_text(yaml_content)

            case = load_case_yaml(case_file)
            default_rubric = [
                RubricCriterion(
                    name="default_criterion", description="Default criterion", weight=1.0
                )
            ]

            chosen_rubric = choose_rubric(case.judge.rubric, default_rubric)

            assert chosen_rubric == case.judge.rubric
            assert len(chosen_rubric) == 1
            assert chosen_rubric[0].name == "custom_criterion"
