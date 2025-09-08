import json
import tempfile
from pathlib import Path

from pondera.io.artifacts import _slug, _summary_md, write_case_artifacts
from pondera.models.case import CaseSpec, CaseInput
from pondera.models.evaluation import EvaluationResult
from pondera.models.judgment import Judgment
from pondera.models.run import RunResult


class TestSlugFunction:
    """Tests for the _slug function."""

    def test_basic_slug(self) -> None:
        """Test basic slug generation."""
        assert _slug("Simple Case") == "simple-case"
        assert _slug("Test123") == "test123"
        assert _slug("UPPERCASE") == "uppercase"

    def test_special_characters(self) -> None:
        """Test slug generation with special characters."""
        assert _slug("Test with spaces & symbols!") == "test-with-spaces-symbols"
        assert _slug("case@#$%^&*()+={}[]") == "case"
        assert _slug("multi___underscore") == "multi___underscore"  # underscores are preserved
        assert _slug("dots.and.more.dots") == "dots-and-more-dots"

    def test_multiple_dashes(self) -> None:
        """Test that multiple consecutive dashes are collapsed."""
        assert _slug("test--double--dash") == "test-double-dash"
        assert _slug("test---triple---dash") == "test-triple-dash"
        assert _slug("test    multiple    spaces") == "test-multiple-spaces"

    def test_leading_trailing_dashes(self) -> None:
        """Test that leading and trailing dashes are stripped."""
        assert _slug("-leading-dash") == "leading-dash"
        assert _slug("trailing-dash-") == "trailing-dash"
        assert _slug("-both-sides-") == "both-sides"
        assert _slug("---multiple---leading---trailing---") == "multiple-leading-trailing"

    def test_whitespace_handling(self) -> None:
        """Test whitespace handling."""
        assert _slug("  leading whitespace") == "leading-whitespace"
        assert _slug("trailing whitespace  ") == "trailing-whitespace"
        assert _slug("  both sides  ") == "both-sides"
        assert _slug("\t\n mixed \r\n whitespace \t") == "mixed-whitespace"

    def test_empty_and_edge_cases(self) -> None:
        """Test empty string and edge cases."""
        assert _slug("") == "case"
        assert _slug("   ") == "case"
        assert _slug("!!!") == "case"
        assert _slug("---") == "case"
        assert _slug("   ---   ") == "case"

    def test_unicode_characters(self) -> None:
        """Test unicode character handling."""
        assert _slug("café résumé") == "café-résumé"  # Unicode letters are preserved
        assert _slug("测试中文") == "测试中文"  # Chinese characters are word characters
        assert _slug("émoji 🚀 test") == "émoji-test"  # Emoji is not a word character

    def test_numbers_and_hyphens(self) -> None:
        """Test that numbers and existing hyphens are preserved."""
        assert _slug("test-123-case") == "test-123-case"
        assert _slug("version-2.0.1") == "version-2-0-1"
        assert _slug("api-v1-endpoint") == "api-v1-endpoint"


class TestSummaryMdFunction:
    """Tests for the _summary_md function."""

    def test_basic_summary(self) -> None:
        """Test basic summary generation."""
        case_input = CaseInput(query="What is 2+2?")
        case = CaseSpec(id="basic-math", input=case_input)
        run = RunResult(question="What is 2+2?", answer_markdown="2+2 equals 4")
        judgment = Judgment(
            score=90,
            pass_fail=True,
            reasoning="Correct answer",
            criteria_scores={"correctness": 90, "clarity": 85},
        )

        evaluation = EvaluationResult(
            case_id="basic-math",
            case=case,
            run=run,
            judgment=judgment,
            overall_threshold=70,
            passed=True,
        )

        summary = _summary_md(evaluation)

        assert "# Case: basic-math" in summary
        assert "**Passed**: ✅" in summary
        assert "**Overall score**: 90 (threshold ≥ 70)" in summary
        assert "**Pre-checks**: passed" in summary
        assert "**correctness**: 90" in summary
        assert "**clarity**: 85" in summary

    def test_failed_case_summary(self) -> None:
        """Test summary for a failed case."""
        case_input = CaseInput(query="Complex question")
        case = CaseSpec(id="failed-case", input=case_input)
        run = RunResult(question="Complex question", answer_markdown="Incomplete answer")
        judgment = Judgment(
            score=40,
            pass_fail=False,
            reasoning="Answer is incomplete",
            criteria_scores={"correctness": 50, "completeness": 30},
            issues=["Missing key information", "Unclear explanation"],
            suggestions=["Add more details", "Improve clarity"],
        )

        evaluation = EvaluationResult(
            case_id="failed-case",
            case=case,
            run=run,
            judgment=judgment,
            precheck_failures=["Missing required keyword"],
            overall_threshold=70,
            per_criterion_thresholds={"correctness": 60, "completeness": 50},
            passed=False,
        )

        summary = _summary_md(evaluation)

        assert "# Case: failed-case" in summary
        assert "**Passed**: ❌" in summary
        assert "**Overall score**: 40 (threshold ≥ 70)" in summary
        assert "**Pre-checks**: FAILED 1" in summary
        assert "**correctness**: 50 (≥ 60)" in summary
        assert "**completeness**: 30 (≥ 50)" in summary
        assert "## Issues" in summary
        assert "- Missing key information" in summary
        assert "- Unclear explanation" in summary
        assert "## Suggestions" in summary
        assert "- Add more details" in summary
        assert "- Improve clarity" in summary
        assert "## Pre-judge check failures" in summary
        assert "- Missing required keyword" in summary

    def test_summary_with_timings(self) -> None:
        """Test summary with timing information."""
        case_input = CaseInput(query="Timed task")
        case = CaseSpec(id="timed-case", input=case_input)
        run = RunResult(question="Timed task")
        judgment = Judgment(score=80, pass_fail=True, reasoning="Good", criteria_scores={})

        evaluation = EvaluationResult(
            case_id="timed-case",
            case=case,
            run=run,
            judgment=judgment,
            overall_threshold=70,
            passed=True,
            timings_s={"runner_s": 5.25, "judge_s": 2.10, "total_s": 7.35},
        )

        summary = _summary_md(evaluation)

        assert "**Timings**: runner=5.25s, judge=2.10s, total=7.35s" in summary

    def test_summary_no_criteria_scores(self) -> None:
        """Test summary with no criteria scores."""
        case_input = CaseInput(query="Simple task")
        case = CaseSpec(id="no-criteria", input=case_input)
        run = RunResult(question="Simple task")
        judgment = Judgment(score=75, pass_fail=True, reasoning="OK", criteria_scores={})

        evaluation = EvaluationResult(
            case_id="no-criteria",
            case=case,
            run=run,
            judgment=judgment,
            overall_threshold=70,
            passed=True,
        )

        summary = _summary_md(evaluation)

        assert "## Criterion scores" in summary
        # Should not have any bullet points for criteria since dict is empty

    def test_summary_missing_timings(self) -> None:
        """Test summary with incomplete timing information."""
        case_input = CaseInput(query="Partial timings")
        case = CaseSpec(id="partial-timings", input=case_input)
        run = RunResult(question="Partial timings")
        judgment = Judgment(
            score=85, pass_fail=True, reasoning="Good", criteria_scores={"quality": 85}
        )

        evaluation = EvaluationResult(
            case_id="partial-timings",
            case=case,
            run=run,
            judgment=judgment,
            overall_threshold=70,
            passed=True,
            timings_s={"runner_s": 3.0},  # Missing judge_s and total_s
        )

        summary = _summary_md(evaluation)

        assert "**Timings**: runner=3.00s, judge=0.00s, total=0.00s" in summary


class TestWriteCaseArtifacts:
    """Tests for the write_case_artifacts function."""

    def test_write_basic_artifacts(self) -> None:
        """Test writing basic case artifacts."""
        case_input = CaseInput(query="What is 2+2?")
        case = CaseSpec(id="math-test", input=case_input)
        run = RunResult(
            question="What is 2+2?",
            answer_markdown="# Answer\n\n2+2 equals 4",
            metadata={"execution_time": 1.5},
        )
        judgment = Judgment(
            score=95,
            pass_fail=True,
            reasoning="Perfect answer",
            criteria_scores={"correctness": 95},
        )

        evaluation = EvaluationResult(
            case_id="math-test",
            case=case,
            run=run,
            judgment=judgment,
            overall_threshold=80,
            passed=True,
            timings_s={"total_s": 2.0},
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            artifacts_root = Path(temp_dir)
            case_dir = write_case_artifacts(artifacts_root, evaluation)

            # Verify case directory was created
            assert case_dir.exists()
            assert case_dir.is_dir()
            assert case_dir.name == "math-test"

            # Verify answer.md
            answer_file = case_dir / "answer.md"
            assert answer_file.exists()
            answer_content = answer_file.read_text(encoding="utf-8")
            assert answer_content == "# Answer\n\n2+2 equals 4"

            # Verify judgment.json
            judgment_file = case_dir / "judgment.json"
            assert judgment_file.exists()
            judgment_data = json.loads(judgment_file.read_text(encoding="utf-8"))
            assert judgment_data["score"] == 95
            assert judgment_data["pass_fail"] is True
            assert judgment_data["reasoning"] == "Perfect answer"
            assert judgment_data["criteria_scores"] == {"correctness": 95}

            # Verify meta.json
            meta_file = case_dir / "meta.json"
            assert meta_file.exists()
            meta_data = json.loads(meta_file.read_text(encoding="utf-8"))
            assert meta_data["case_id"] == "math-test"
            assert meta_data["passed"] is True
            assert meta_data["overall_threshold"] == 80
            assert meta_data["timings_s"] == {"total_s": 2.0}
            assert meta_data["runner_metadata"] == {"execution_time": 1.5}

            # Verify summary.md
            summary_file = case_dir / "summary.md"
            assert summary_file.exists()
            summary_content = summary_file.read_text(encoding="utf-8")
            assert "# Case: math-test" in summary_content
            assert "**Passed**: ✅" in summary_content

    def test_write_artifacts_with_complex_case_id(self) -> None:
        """Test writing artifacts with complex case ID that needs slugification."""
        case_input = CaseInput(query="Complex test")
        case = CaseSpec(id="Complex Test Case #1 (Special Characters!)", input=case_input)
        run = RunResult(question="Complex test")
        judgment = Judgment(score=80, pass_fail=True, reasoning="Good", criteria_scores={})

        evaluation = EvaluationResult(
            case_id="Complex Test Case #1 (Special Characters!)",
            case=case,
            run=run,
            judgment=judgment,
            overall_threshold=70,
            passed=True,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            artifacts_root = Path(temp_dir)
            case_dir = write_case_artifacts(artifacts_root, evaluation)

            # Verify the directory name is properly slugified
            assert case_dir.name == "complex-test-case-1-special-characters"
            assert case_dir.exists()

    def test_write_artifacts_path_as_string(self) -> None:
        """Test that the function accepts string paths."""
        case_input = CaseInput(query="String path test")
        case = CaseSpec(id="string-path", input=case_input)
        run = RunResult(question="String path test")
        judgment = Judgment(score=70, pass_fail=True, reasoning="OK", criteria_scores={})

        evaluation = EvaluationResult(
            case_id="string-path",
            case=case,
            run=run,
            judgment=judgment,
            overall_threshold=60,
            passed=True,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            # Pass string instead of Path
            case_dir = write_case_artifacts(temp_dir, evaluation)

            assert case_dir.exists()
            assert case_dir.name == "string-path"
            assert (case_dir / "answer.md").exists()
            assert (case_dir / "judgment.json").exists()
            assert (case_dir / "meta.json").exists()
            assert (case_dir / "summary.md").exists()

    def test_write_artifacts_empty_answer(self) -> None:
        """Test writing artifacts when answer is empty."""
        case_input = CaseInput(query="Empty answer test")
        case = CaseSpec(id="empty-answer", input=case_input)
        run = RunResult(question="Empty answer test", answer_markdown="")
        judgment = Judgment(
            score=0, pass_fail=False, reasoning="No answer provided", criteria_scores={}
        )

        evaluation = EvaluationResult(
            case_id="empty-answer",
            case=case,
            run=run,
            judgment=judgment,
            overall_threshold=50,
            passed=False,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            artifacts_root = Path(temp_dir)
            case_dir = write_case_artifacts(artifacts_root, evaluation)

            # Verify answer.md exists but is empty
            answer_file = case_dir / "answer.md"
            assert answer_file.exists()
            assert answer_file.read_text(encoding="utf-8") == ""

    def test_write_artifacts_none_answer(self) -> None:
        """Test writing artifacts when answer is None."""
        case_input = CaseInput(query="None answer test")
        case = CaseSpec(id="none-answer", input=case_input)
        run = RunResult(question="None answer test")  # answer_markdown defaults to ""
        judgment = Judgment(score=0, pass_fail=False, reasoning="No answer", criteria_scores={})

        evaluation = EvaluationResult(
            case_id="none-answer",
            case=case,
            run=run,
            judgment=judgment,
            overall_threshold=50,
            passed=False,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            artifacts_root = Path(temp_dir)
            case_dir = write_case_artifacts(artifacts_root, evaluation)

            # Verify answer.md exists and is empty (since answer_markdown defaults to "")
            answer_file = case_dir / "answer.md"
            assert answer_file.exists()
            assert answer_file.read_text(encoding="utf-8") == ""

    def test_write_artifacts_creates_parent_directories(self) -> None:
        """Test that parent directories are created if they don't exist."""
        case_input = CaseInput(query="Nested path test")
        case = CaseSpec(id="nested-test", input=case_input)
        run = RunResult(question="Nested path test")
        judgment = Judgment(score=75, pass_fail=True, reasoning="Good", criteria_scores={})

        evaluation = EvaluationResult(
            case_id="nested-test",
            case=case,
            run=run,
            judgment=judgment,
            overall_threshold=70,
            passed=True,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a nested path that doesn't exist
            nested_path = Path(temp_dir) / "deeply" / "nested" / "artifacts"
            case_dir = write_case_artifacts(nested_path, evaluation)

            assert case_dir.exists()
            assert case_dir.parent == nested_path
            assert (case_dir / "summary.md").exists()

    def test_write_artifacts_unicode_content(self) -> None:
        """Test writing artifacts with unicode content."""
        case_input = CaseInput(query="Unicode test: café résumé 测试")
        case = CaseSpec(id="unicode-test", input=case_input)
        run = RunResult(
            question="Unicode test",
            answer_markdown="# Réponse\n\nCafé ☕ and résumé 📄\n\n测试中文",
        )
        judgment = Judgment(
            score=85,
            pass_fail=True,
            reasoning="Unicode content handled well: café ☕",
            criteria_scores={"unicode_handling": 90},
        )

        evaluation = EvaluationResult(
            case_id="unicode-test",
            case=case,
            run=run,
            judgment=judgment,
            overall_threshold=70,
            passed=True,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            artifacts_root = Path(temp_dir)
            case_dir = write_case_artifacts(artifacts_root, evaluation)

            # Verify unicode content is preserved
            answer_file = case_dir / "answer.md"
            answer_content = answer_file.read_text(encoding="utf-8")
            assert "Café ☕" in answer_content
            assert "résumé 📄" in answer_content
            assert "测试中文" in answer_content

            # Verify unicode in JSON
            judgment_file = case_dir / "judgment.json"
            judgment_data = json.loads(judgment_file.read_text(encoding="utf-8"))
            assert "café ☕" in judgment_data["reasoning"]
