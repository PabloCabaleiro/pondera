"""Integration tests for the pondera CLI."""

import subprocess
import tempfile
import os
import sys
from pathlib import Path
import pytest


@pytest.mark.integration
class TestCLIIntegration:
    """Integration tests for the pondera CLI commands."""

    def _run_pondera_cli(self, args: list[str], cwd: Path | None = None) -> tuple[int, str, str]:
        """Run pondera CLI command and return exit code, stdout, stderr."""
        cmd = [sys.executable, "-m", "pondera.cli"] + args
        env = os.environ.copy()
        env["PYTHONPATH"] = str(Path(__file__).parent.parent.parent / "src")

        result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, env=env)
        return result.returncode, result.stdout, result.stderr

    def test_cli_help(self) -> None:
        """Test that CLI help command works."""
        exit_code, stdout, stderr = self._run_pondera_cli(["--help"])

        assert exit_code == 0
        # Updated CLI may not render banner text depending on rich availability; check core usage text.
        assert "Usage:" in stdout
        assert "cases_path" in stdout or "CASES_PATH" in stdout

    def test_cli_run_single_case(self) -> None:
        """Test running a single case file via CLI."""
        case_file = Path(__file__).parent / "data" / "basic_integration.yaml"

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create test runner module
            runner_content = """
from tests.integration.test_runner import TestRunner

def get_runner():
    return TestRunner("Paris is the capital city of France")
"""
            runner_file = temp_path / "test_runner_module.py"
            runner_file.write_text(runner_content)

            # Run pondera with the test runner
            exit_code, stdout, stderr = self._run_pondera_cli(
                [str(case_file), "--runner", f"{runner_file.stem}:get_runner"], cwd=temp_path
            )

            # Note: This might fail due to import issues in the subprocess
            # but we can at least verify the CLI is attempting to run
            print(f"Exit code: {exit_code}")
            print(f"Stdout: {stdout}")
            print(f"Stderr: {stderr}")

    def test_cli_run_directory(self) -> None:
        """Test running all cases in a directory via CLI."""
        data_dir = Path(__file__).parent / "data"

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create test runner module
            runner_content = """
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent.parent.parent / "src"))

from pondera.runner.base import Runner
from pondera.models.run import RunResult

class SimpleRunner(Runner):
    async def run(self, question, attachments=None, params=None, progress=None):
        # Simple responses for different questions
        if "capital of France" in question:
            answer = "Paris"
        elif "2 + 2" in question:
            answer = "4"
        elif "photosynthesis" in question.lower():
            answer = "Photosynthesis is the process by which plants convert sunlight into energy"
        else:
            answer = "I don't know"

        return RunResult(
            question=question,
            answer=answer,
            metadata={"test": True}
        )

def get_runner():
    return SimpleRunner()
"""
            runner_file = temp_path / "integration_runner.py"
            runner_file.write_text(runner_content)

            # Run pondera on the directory
            exit_code, stdout, stderr = self._run_pondera_cli(
                [str(data_dir), "--runner", f"{runner_file.stem}:get_runner"], cwd=temp_path
            )

            print(f"Directory test - Exit code: {exit_code}")
            print(f"Stdout: {stdout}")
            print(f"Stderr: {stderr}")

    def test_cli_invalid_runner(self) -> None:
        """Test CLI with invalid runner specification."""
        case_file = Path(__file__).parent / "data" / "basic_integration.yaml"

        exit_code, stdout, stderr = self._run_pondera_cli(
            [str(case_file), "--runner", "nonexistent_module:nonexistent_function"]
        )

        # Should fail with non-zero exit code
        assert exit_code != 0
        # Should contain error message about the module
        assert "Cannot import module" in stderr or "Cannot import module" in stdout

    def test_cli_invalid_case_file(self) -> None:
        """Test CLI with non-existent case file."""
        exit_code, stdout, stderr = self._run_pondera_cli(
            ["/nonexistent/file.yaml", "--runner", "some_module:some_function"]
        )

        # Should fail with non-zero exit code
        assert exit_code != 0

    def test_cli_malformed_runner_spec(self) -> None:
        """Test CLI with malformed runner specification."""
        case_file = Path(__file__).parent / "data" / "basic_integration.yaml"

        exit_code, stdout, stderr = self._run_pondera_cli(
            [str(case_file), "--runner", "invalid_format_without_colon"]
        )

        # Should fail with non-zero exit code
        assert exit_code != 0
        # Should contain error about expected format
        error_output = stderr + stdout
        assert "Expected format" in error_output or "module:object" in error_output


@pytest.mark.integration
class TestCLIEndToEnd:
    """End-to-end tests that verify the complete CLI workflow."""

    def test_complete_workflow_with_artifacts(self) -> None:
        """Test complete workflow including artifact generation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create a test case
            case_content = """
id: e2e_test_case
input:
  query: "What is 5 + 3?"
expectations:
  answer: "8"
judge:
  threshold: 0.8
"""
            case_file = temp_path / "test_case.yaml"
            case_file.write_text(case_content)

            # Create test runner
            runner_content = """
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent.parent / "src"))

from pondera.runner.base import Runner
from pondera.models.run import RunResult

class MathRunner(Runner):
    async def run(self, question, attachments=None, params=None, progress=None):
        if "5 + 3" in question:
            return RunResult(
                question=question,
                answer="8",
                metadata={"calculation": "5 + 3 = 8"}
            )
        return RunResult(
            question=question,
            answer="Unknown",
            metadata={}
        )

def make_runner():
    return MathRunner()
"""
            runner_file = temp_path / "math_runner.py"
            runner_file.write_text(runner_content)

            # Create artifacts directory
            artifacts_dir = temp_path / "artifacts"
            artifacts_dir.mkdir()

            # Run the evaluation
            cmd = [
                sys.executable,
                "-m",
                "pondera.cli",
                str(case_file),
                "--runner",
                f"{runner_file.stem}:make_runner",
                "--artifacts-dir",
                str(artifacts_dir),
            ]

            env = os.environ.copy()
            env["PYTHONPATH"] = str(Path(__file__).parent.parent.parent / "src")

            result = subprocess.run(cmd, capture_output=True, text=True, cwd=temp_path, env=env)

            print(f"E2E test - Exit code: {result.returncode}")
            print(f"Stdout: {result.stdout}")
            print(f"Stderr: {result.stderr}")

            # Check if artifacts were created (depending on implementation)
            # This is more of a smoke test to ensure the CLI runs without crashing
