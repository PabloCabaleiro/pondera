"""Tests for pondera.cli module."""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
from typing import Any

import typer
from typer.testing import CliRunner

from pondera.cli import app, _iter_case_files, _load_runner, run_cases
from pondera.models.run import RunResult
from pondera.models.evaluation import EvaluationResult
from pondera.models.case import CaseSpec, CaseInput, CaseJudge
from pondera.models.judgment import Judgment


class MockJudge:
    """Mock judge for CLI testing."""

    async def judge(
        self,
        *,
        question: str,
        answer_markdown: str,
        judge_request: str,
        rubric: list[Any] | None = None,
        model: str | None = None,
        system_append: str = "",
    ) -> Judgment:
        return Judgment(reasoning="Mock reasoning", score=0.8, max_score=1.0)


class MockRunner:
    """Mock runner for CLI testing."""

    async def run(
        self,
        *,
        question: str,
        attachments: list[str] | None = None,
        params: dict[str, Any] | None = None,
        progress: Any = None,
    ) -> RunResult:
        return RunResult(question=question, answer_markdown="Mock answer")


def create_mock_runner() -> MockRunner:
    """Factory function for mock runner."""
    return MockRunner()


class MockRunnerClass:
    """Class-based mock runner."""

    async def run(
        self,
        *,
        question: str,
        attachments: list[str] | None = None,
        params: dict[str, Any] | None = None,
        progress: Any = None,
    ) -> RunResult:
        return RunResult(question=question, answer_markdown="Class runner answer")


# Mock module for testing imports
mock_module = Mock()
mock_module.create_mock_runner = create_mock_runner
mock_module.MockRunner = MockRunner
mock_module.MockRunnerClass = MockRunnerClass
mock_module.mock_runner_instance = MockRunner()


class TestIterCaseFiles:
    """Test the _iter_case_files utility function."""

    def test_finds_yaml_files(self) -> None:
        """Test that both .yaml and .yml files are found."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cases_dir = Path(tmpdir)

            # Create test files
            (cases_dir / "case1.yaml").write_text("id: case1\ninput:\n  query: test")
            (cases_dir / "case2.yml").write_text("id: case2\ninput:\n  query: test")
            (cases_dir / "not_case.txt").write_text("not a case")

            # Create subdirectory with files
            subdir = cases_dir / "subdir"
            subdir.mkdir()
            (subdir / "case3.yaml").write_text("id: case3\ninput:\n  query: test")

            files = list(_iter_case_files(cases_dir))

            # Should find 3 files (case1.yaml, case2.yml, subdir/case3.yaml)
            assert len(files) == 3
            assert any(f.name == "case1.yaml" for f in files)
            assert any(f.name == "case2.yml" for f in files)
            assert any(f.name == "case3.yaml" for f in files)
            assert not any(f.name == "not_case.txt" for f in files)

    def test_empty_directory(self) -> None:
        """Test that empty directory returns no files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cases_dir = Path(tmpdir)
            files = list(_iter_case_files(cases_dir))
            assert files == []

    def test_sorted_order(self) -> None:
        """Test that files are returned in sorted order."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cases_dir = Path(tmpdir)

            # Create files in reverse alphabetical order
            (cases_dir / "z_case.yaml").write_text("id: z_case\ninput:\n  query: test")
            (cases_dir / "b_case.yaml").write_text("id: b_case\ninput:\n  query: test")
            (cases_dir / "a_case.yaml").write_text("id: a_case\ninput:\n  query: test")

            files = list(_iter_case_files(cases_dir))
            file_names = [f.name for f in files]

            assert file_names == ["a_case.yaml", "b_case.yaml", "z_case.yaml"]


class TestLoadRunner:
    """Test the _load_runner function."""

    def test_factory_function(self) -> None:
        """Test loading a runner from a factory function."""
        with patch("importlib.import_module", return_value=mock_module):
            runner = _load_runner("test_module:create_mock_runner")
            assert isinstance(runner, MockRunner)

    def test_class_instantiation(self) -> None:
        """Test loading a runner from a class."""
        with patch("importlib.import_module", return_value=mock_module):
            runner = _load_runner("test_module:MockRunnerClass")
            assert isinstance(runner, MockRunnerClass)

    def test_instance_loading(self) -> None:
        """Test loading a pre-instantiated runner."""
        with patch("importlib.import_module", return_value=mock_module):
            runner = _load_runner("test_module:mock_runner_instance")
            assert isinstance(runner, MockRunner)

    def test_invalid_format(self) -> None:
        """Test error handling for invalid target format."""
        with pytest.raises(typer.BadParameter) as exc_info:
            _load_runner("invalid_format")

        assert "Expected format 'module:object'" in str(exc_info.value)

    def test_module_not_found(self) -> None:
        """Test error handling for module import failure."""
        with patch("importlib.import_module", side_effect=ModuleNotFoundError("No module")):
            with pytest.raises(typer.BadParameter) as exc_info:
                _load_runner("nonexistent:runner")

            assert "Cannot import module 'nonexistent'" in str(exc_info.value)

    def test_attribute_not_found(self) -> None:
        """Test error handling for missing attribute."""
        empty_module = Mock()
        del empty_module.nonexistent_runner  # Ensure attribute doesn't exist

        with patch("importlib.import_module", return_value=empty_module):
            with pytest.raises(typer.BadParameter) as exc_info:
                _load_runner("test_module:nonexistent_runner")

            assert "has no attribute 'nonexistent_runner'" in str(exc_info.value)

    def test_factory_returns_invalid_object(self) -> None:
        """Test error handling when factory returns object without run method."""

        def bad_factory() -> str:
            return "not a runner"

        bad_module = Mock()
        bad_module.bad_factory = bad_factory

        with patch("importlib.import_module", return_value=bad_module):
            with pytest.raises(typer.BadParameter) as exc_info:
                _load_runner("test_module:bad_factory")

            assert "did not return an object with a 'run' method" in str(exc_info.value)

    def test_class_without_run_method(self) -> None:
        """Test error handling for class without run method."""

        class BadRunner:
            pass

        bad_module = Mock()
        bad_module.BadRunner = BadRunner

        with patch("importlib.import_module", return_value=bad_module):
            with pytest.raises(typer.BadParameter) as exc_info:
                _load_runner("test_module:BadRunner")

            assert "does not define a 'run' method" in str(exc_info.value)

    def test_object_without_run_method(self) -> None:
        """Test error handling for object without run method."""
        bad_object = "not a runner"

        bad_module = Mock()
        bad_module.bad_object = bad_object

        with patch("importlib.import_module", return_value=bad_module):
            with pytest.raises(typer.BadParameter) as exc_info:
                _load_runner("test_module:bad_object")

            assert "is not a runner (missing 'run' method)" in str(exc_info.value)


class TestRunCasesCommand:
    """Test the run_cases CLI command."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.runner = CliRunner()
        self.test_data_dir = Path(__file__).parent / "data"
        self.mock_evaluation_result = EvaluationResult(
            case_id="test-case",
            case=CaseSpec(
                id="test-case", input=CaseInput(query="Test question"), judge=CaseJudge()
            ),
            run=RunResult(question="Test question", answer_markdown="Test answer"),
            judgment=Judgment(
                score=85, pass_fail=True, reasoning="Good answer", criteria_scores={"accuracy": 90}
            ),
            overall_threshold=70,
            passed=True,
            timings_s={"runner_s": 0.5, "judge_s": 0.3},
        )

    def create_sample_yaml(self, path: Path) -> None:
        """Create a sample YAML case file."""
        yaml_content = """id: test-case
input:
  query: "What is the capital of France?"
  attachments: []
  params: {}
judge:
  request: "Judge the accuracy of this answer"
  overall_threshold: 70
"""
        path.write_text(yaml_content)

    def test_basic_success(self) -> None:
        """Test basic successful execution of run_cases command."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Mock all the dependencies before calling the function
            with (
                patch("pondera.cli._load_runner") as mock_load_runner,
                patch("pondera.cli.Judge") as mock_judge_cls,
                patch("pondera.cli.evaluate_case_async") as mock_evaluate,
                patch("pondera.cli.write_case_artifacts") as mock_write,
                patch("pondera.cli.get_settings") as mock_settings,
                patch("pondera.cli.typer.echo") as mock_echo,
            ):
                # Setup mock returns
                mock_load_runner.return_value = MockRunner()
                mock_judge_cls.return_value = Mock()
                mock_evaluate.return_value = self.mock_evaluation_result
                mock_write.return_value = None

                mock_settings_obj = Mock()
                mock_settings_obj.artifacts_dir = str(Path(tmpdir) / "artifacts")
                mock_settings.return_value = mock_settings_obj

                # Call the function directly
                try:
                    run_cases(
                        cases_dir=self.test_data_dir,
                        runner="test:runner",
                        artifacts=None,
                        judge_model=None,
                        fail_fast=False,
                    )
                    # If we get here without exception, test passed
                    success = True
                except typer.Exit as e:
                    # Exit code 0 means success
                    success = e.exit_code == 0

                assert success
                # Verify that echo was called with PASS messages
                echo_calls = [call[0][0] for call in mock_echo.call_args_list if call[0]]
                pass_messages = [msg for msg in echo_calls if "PASS ✅" in msg]
                assert len(pass_messages) == 6  # Should have 6 passing cases

    def test_with_custom_artifacts_dir(self) -> None:
        """Test run_cases with custom artifacts directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            artifacts_dir = Path(tmpdir) / "custom_artifacts"

            with (
                patch("pondera.cli._load_runner", return_value=MockRunner()),
                patch("pondera.cli.Judge"),
                patch("pondera.cli.evaluate_case_async", return_value=self.mock_evaluation_result),
                patch("pondera.cli.write_case_artifacts"),
                patch("pondera.cli.get_settings"),
                patch("pondera.cli.typer.echo"),
            ):
                try:
                    run_cases(
                        cases_dir=self.test_data_dir,
                        runner="test:runner",
                        artifacts=artifacts_dir,
                        judge_model=None,
                        fail_fast=False,
                    )
                    success = True
                except typer.Exit as e:
                    success = e.exit_code == 0

                assert success
                assert artifacts_dir.exists()

    def test_with_judge_model_override(self) -> None:
        """Test run_cases with custom judge model."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with (
                patch("pondera.cli._load_runner", return_value=MockRunner()),
                patch("pondera.cli.Judge") as mock_judge,
                patch("pondera.cli.evaluate_case_async", return_value=self.mock_evaluation_result),
                patch("pondera.cli.write_case_artifacts"),
                patch("pondera.cli.get_settings") as mock_settings,
                patch("pondera.cli.typer.echo"),
            ):
                mock_settings.return_value.artifacts_dir = str(Path(tmpdir) / "artifacts")

                try:
                    run_cases(
                        cases_dir=self.test_data_dir,
                        runner="test:runner",
                        artifacts=None,
                        judge_model="gpt-4",
                        fail_fast=False,
                    )
                    success = True
                except typer.Exit as e:
                    success = e.exit_code == 0

                assert success
                mock_judge.assert_called_once_with(model="gpt-4")

    def test_no_yaml_files(self) -> None:
        """Test error handling when no YAML files are found."""
        with tempfile.TemporaryDirectory() as tmpdir:
            empty_dir = Path(tmpdir)
            # Don't create any YAML files

            with (
                patch("pondera.cli._load_runner", return_value=MockRunner()),
                patch("pondera.cli.Judge", return_value=MockJudge()),
                patch("pondera.cli.typer.echo") as mock_echo,
            ):
                try:
                    run_cases(
                        cases_dir=empty_dir,
                        runner="test:runner",
                        artifacts=None,
                        judge_model=None,
                        fail_fast=False,
                    )
                    success = False  # Should not reach here
                except typer.Exit as e:
                    success = e.exit_code == 2  # Should exit with code 2

                assert success
                # Check that error message was echoed
                echo_calls = [call[0][0] for call in mock_echo.call_args_list if call[0]]
                error_messages = [msg for msg in echo_calls if "No YAML cases found" in msg]
                assert len(error_messages) >= 1

    def test_failed_case(self) -> None:
        """Test handling of failed test cases."""
        failed_result = EvaluationResult(
            case_id="test-case",
            case=CaseSpec(
                id="test-case", input=CaseInput(query="Test question"), judge=CaseJudge()
            ),
            run=RunResult(question="Test question", answer_markdown="Test answer"),
            judgment=Judgment(
                score=50, pass_fail=False, reasoning="Poor answer", criteria_scores={"accuracy": 50}
            ),
            overall_threshold=70,
            passed=False,
            timings_s={"runner_s": 0.5, "judge_s": 0.3},
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            with (
                patch("pondera.cli._load_runner", return_value=MockRunner()),
                patch("pondera.cli.Judge"),
                patch("pondera.cli.evaluate_case_async", return_value=failed_result),
                patch("pondera.cli.write_case_artifacts"),
                patch("pondera.cli.get_settings") as mock_settings,
                patch("pondera.cli.typer.echo") as mock_echo,
            ):
                mock_settings.return_value.artifacts_dir = str(Path(tmpdir) / "artifacts")

                try:
                    run_cases(
                        cases_dir=self.test_data_dir,
                        runner="test:runner",
                        artifacts=None,
                        judge_model=None,
                        fail_fast=False,
                    )
                    success = False  # Should not reach here
                except typer.Exit as e:
                    success = e.exit_code == 1  # Should exit with code 1 for failures

                assert success
                # Verify that echo was called with FAIL messages
                echo_calls = [call[0][0] for call in mock_echo.call_args_list if call[0]]
                fail_messages = [msg for msg in echo_calls if "FAIL ❌" in msg]
                assert len(fail_messages) == 6  # Should have 6 failing cases

    def test_fail_fast(self) -> None:
        """Test fail-fast behavior."""
        failed_result = EvaluationResult(
            case_id="test-case",
            case=CaseSpec(
                id="test-case", input=CaseInput(query="Test question"), judge=CaseJudge()
            ),
            run=RunResult(question="Test question", answer_markdown="Test answer"),
            judgment=Judgment(
                score=50, pass_fail=False, reasoning="Poor answer", criteria_scores={"accuracy": 50}
            ),
            overall_threshold=70,
            passed=False,
            timings_s={"runner_s": 0.5, "judge_s": 0.3},
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            with (
                patch("pondera.cli._load_runner", return_value=MockRunner()),
                patch("pondera.cli.Judge"),
                patch("pondera.cli.evaluate_case_async", return_value=failed_result),
                patch("pondera.cli.write_case_artifacts"),
                patch("pondera.cli.get_settings") as mock_settings,
                patch("pondera.cli.typer.echo") as mock_echo,
            ):
                mock_settings.return_value.artifacts_dir = str(Path(tmpdir) / "artifacts")

                try:
                    run_cases(
                        cases_dir=self.test_data_dir,
                        runner="test:runner",
                        artifacts=None,
                        judge_model=None,
                        fail_fast=True,
                    )
                    success = False  # Should not reach here
                except typer.Exit as e:
                    success = e.exit_code == 1  # Should exit with code 1 for failure

                assert success
                # Should only see one test case processed due to fail-fast
                # The first file alphabetically is basic_test.yaml
                echo_calls = [call[0][0] for call in mock_echo.call_args_list if call[0]]
                case_messages = [msg for msg in echo_calls if "Running case:" in msg]
                assert len(case_messages) == 1  # Should only process one case

    def test_exception_handling(self) -> None:
        """Test error handling when evaluation raises an exception."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with (
                patch("pondera.cli._load_runner", return_value=MockRunner()),
                patch("pondera.cli.Judge"),
                patch(
                    "pondera.cli.evaluate_case_async", side_effect=Exception("Evaluation failed")
                ),
                patch("pondera.cli.write_case_artifacts"),
                patch("pondera.cli.get_settings") as mock_settings,
                patch("pondera.cli.typer.echo") as mock_echo,
            ):
                mock_settings.return_value.artifacts_dir = str(Path(tmpdir) / "artifacts")

                try:
                    run_cases(
                        cases_dir=self.test_data_dir,
                        runner="test:runner",
                        artifacts=None,
                        judge_model=None,
                        fail_fast=False,
                    )
                    success = False  # Should not reach here
                except typer.Exit as e:
                    success = e.exit_code == 1  # Should exit with code 1 for errors

                assert success
                # Check that error messages were echoed
                echo_calls = [call[0][0] for call in mock_echo.call_args_list if call[0]]
                error_messages = [msg for msg in echo_calls if "Error while running" in msg]
                assert len(error_messages) >= 1

    def test_discovers_test_data_files(self) -> None:
        """Test that the CLI discovers all test YAML files in tests/data."""
        from pondera.cli import _iter_case_files

        files = list(_iter_case_files(self.test_data_dir))
        file_names = [f.name for f in files]

        # Should find all 6 YAML files
        expected_files = [
            "basic_test.yaml",
            "complex_reasoning.yaml",
            "genes_per_chr.yaml",
            "high_threshold_test.yaml",
            "math_problem.yml",
            "nested_test.yaml",  # from subdirectory
        ]

        assert len(files) == 6
        for expected_file in expected_files:
            assert expected_file in file_names


class TestAppIntegration:
    """Integration tests for the CLI app."""

    def test_app_help(self) -> None:
        """Test that the app shows help correctly."""
        runner = CliRunner()
        result = runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        assert "run" in result.stdout  # Should show the run command

    def test_run_command_help(self) -> None:
        """Test that the run command shows help correctly."""
        runner = CliRunner()
        result = runner.invoke(app, ["run", "--help"])

        assert result.exit_code == 0
        assert "Run all YAML cases" in result.stdout
        assert "--runner" in result.stdout
        assert "--artifacts" in result.stdout
        assert "--judge-model" in result.stdout
        assert "--fail-fast" in result.stdout
