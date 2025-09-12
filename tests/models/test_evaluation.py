import pytest
from pydantic import ValidationError

from pondera.models.evaluation import EvaluationResult
from pondera.models.case import CaseSpec, CaseInput
from pondera.models.run import RunResult
from pondera.models.judgment import Judgment


class TestEvaluationResult:
    """Tests for EvaluationResult model."""

    def test_minimal_evaluation_result(self) -> None:
        """Test creating evaluation result with minimal required fields."""
        case_input = CaseInput(query="What is 2+2?")
        case = CaseSpec(id="test-case", input=case_input)
        run = RunResult(question="What is 2+2?")
        judgment = Judgment(
            score=85,
            pass_fail=True,
            reasoning="Correct answer",
            criteria_scores={"correctness": 85},
        )

        evaluation = EvaluationResult(
            case_id="test-case",
            case=case,
            run=run,
            judgment=judgment,
            overall_threshold=70,
            passed=True,
        )

        assert evaluation.case_id == "test-case"
        assert evaluation.case.id == "test-case"
        assert evaluation.run.question == "What is 2+2?"
        assert evaluation.judgment.score == 85
        assert evaluation.precheck_failures == []
        assert evaluation.overall_threshold == 70
        assert evaluation.per_criterion_thresholds == {}
        assert evaluation.passed is True
        assert evaluation.timings_s == {}

    def test_full_evaluation_result(self) -> None:
        """Test creating evaluation result with all fields."""
        case_input = CaseInput(
            query="Analyze this data", attachments=["data.csv"], params={"format": "json"}
        )
        case = CaseSpec(id="analysis-case", input=case_input)
        run = RunResult(
            question="Analyze this data",
            answer="# Analysis\n\nThe data shows trends...",
            artifacts=["chart.png"],
            metadata={"execution_time": 5.2},
        )
        judgment = Judgment(
            score=75,
            pass_fail=True,
            reasoning="Good analysis with minor issues",
            criteria_scores={"correctness": 80, "completeness": 70},
            issues=["Missing trend explanation"],
            suggestions=["Add more details about trends"],
        )

        evaluation = EvaluationResult(
            case_id="analysis-case",
            case=case,
            run=run,
            judgment=judgment,
            precheck_failures=["Missing required keyword"],
            overall_threshold=70,
            per_criterion_thresholds={"correctness": 75, "completeness": 65},
            passed=True,
            timings_s={"runner": 5.2, "judge": 2.1, "precheck": 0.3, "total": 7.6},
        )

        assert evaluation.case_id == "analysis-case"
        assert evaluation.case.input.query == "Analyze this data"
        assert evaluation.run.answer.startswith("# Analysis")
        assert evaluation.judgment.score == 75
        assert evaluation.precheck_failures == ["Missing required keyword"]
        assert evaluation.overall_threshold == 70
        assert evaluation.per_criterion_thresholds == {"correctness": 75, "completeness": 65}
        assert evaluation.passed is True
        assert evaluation.timings_s["runner"] == 5.2
        assert evaluation.timings_s["total"] == 7.6

    def test_failed_evaluation(self) -> None:
        """Test evaluation result for a failed case."""
        case_input = CaseInput(query="What is the capital of Mars?")
        case = CaseSpec(id="impossible-case", input=case_input)
        run = RunResult(
            question="What is the capital of Mars?",
            answer="Mars doesn't have a capital city.",
        )
        judgment = Judgment(
            score=45,
            pass_fail=False,
            reasoning="Factually incorrect assumption in question",
            criteria_scores={"correctness": 50, "completeness": 40},
            issues=["Question is based on false premise"],
            suggestions=["Clarify that Mars has no cities"],
        )

        evaluation = EvaluationResult(
            case_id="impossible-case",
            case=case,
            run=run,
            judgment=judgment,
            precheck_failures=["Answer too short"],
            overall_threshold=70,
            passed=False,
        )

        assert evaluation.case_id == "impossible-case"
        assert evaluation.judgment.score == 45
        assert evaluation.judgment.pass_fail is False
        assert evaluation.precheck_failures == ["Answer too short"]
        assert evaluation.passed is False

    def test_precheck_failures_list(self) -> None:
        """Test that precheck failures can contain multiple items."""
        case_input = CaseInput(query="Test question")
        case = CaseSpec(id="test", input=case_input)
        run = RunResult(question="Test question")
        judgment = Judgment(score=60, pass_fail=True, reasoning="OK", criteria_scores={})

        evaluation = EvaluationResult(
            case_id="test",
            case=case,
            run=run,
            judgment=judgment,
            precheck_failures=[
                "Missing keyword 'analysis'",
                "Contains forbidden word 'error'",
                "Regex pattern not matched",
            ],
            overall_threshold=50,
            passed=False,
        )

        assert len(evaluation.precheck_failures) == 3
        assert "Missing keyword 'analysis'" in evaluation.precheck_failures
        assert "Contains forbidden word 'error'" in evaluation.precheck_failures
        assert "Regex pattern not matched" in evaluation.precheck_failures

    def test_complex_timings(self) -> None:
        """Test that timings can contain various timing measurements."""
        case_input = CaseInput(query="Complex task")
        case = CaseSpec(id="complex", input=case_input)
        run = RunResult(question="Complex task")
        judgment = Judgment(score=90, pass_fail=True, reasoning="Excellent", criteria_scores={})

        evaluation = EvaluationResult(
            case_id="complex",
            case=case,
            run=run,
            judgment=judgment,
            overall_threshold=80,
            passed=True,
            timings_s={
                "runner_init": 0.5,
                "runner_execution": 10.2,
                "runner_cleanup": 0.3,
                "precheck": 0.1,
                "judge_init": 0.2,
                "judge_execution": 3.5,
                "threshold_evaluation": 0.05,
                "total": 14.85,
            },
        )

        assert evaluation.timings_s["runner_execution"] == 10.2
        assert evaluation.timings_s["judge_execution"] == 3.5
        assert evaluation.timings_s["total"] == 14.85

    def test_missing_required_fields(self) -> None:
        """Test that missing required fields raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            EvaluationResult()  # type: ignore

        error_str = str(exc_info.value)
        assert "Field required" in error_str

    def test_extra_fields_forbidden(self) -> None:
        """Test that extra fields are forbidden."""
        case_input = CaseInput(query="test")
        case = CaseSpec(id="test", input=case_input)
        run = RunResult(question="test")
        judgment = Judgment(score=80, pass_fail=True, reasoning="test", criteria_scores={})

        with pytest.raises(ValidationError) as exc_info:
            EvaluationResult(
                case_id="test",
                case=case,
                run=run,
                judgment=judgment,
                overall_threshold=70,
                passed=True,
                extra_field="not allowed",  # type: ignore
            )

        assert "Extra inputs are not permitted" in str(exc_info.value)
