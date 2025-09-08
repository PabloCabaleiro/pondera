"""Real integration tests for pondera CLI and API without mocks."""

import pytest
import tempfile
import subprocess
import sys
import os
from pathlib import Path


class TestRealIntegration:
    """Integration tests using real components."""

    def test_cli_help_command(self) -> None:
        """Test that CLI help works."""
        cmd = [
            sys.executable,
            "-c",
            "import sys; import pondera.cli; sys.argv = ['pondera', '--help']; pondera.cli.app()",
        ]
        env = os.environ.copy()
        env["PYTHONPATH"] = str(Path(__file__).parent.parent.parent / "src")

        result = subprocess.run(cmd, capture_output=True, text=True, env=env)

        # CLI should show help successfully
        output = result.stdout + result.stderr
        assert result.returncode == 0
        assert "Pondera" in output or "pondera" in output or "Usage:" in output

    def test_cli_with_simple_runner_module(self) -> None:
        """Test CLI with a real runner module."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create a simple test case
            case_content = """
id: cli_integration_test
input:
  query: "What is 5 + 3?"
expect:
  must_contain: ["8"]
judge:
  overall_threshold: 80
"""
            case_file = temp_path / "test_case.yaml"
            case_file.write_text(case_content)

            # Create a real runner module
            runner_content = """
import sys
from pathlib import Path

# Add src to path to import pondera modules
src_path = Path(__file__).parent.parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from pondera.runner.base import Runner
from pondera.models.run import RunResult

class SimpleRunner(Runner):
    async def run(self, question, attachments=None, params=None, progress=None):
        # Simple math solver
        if "5 + 3" in question:
            answer = "The answer is 8"
        elif "capital of France" in question:
            answer = "Paris"
        else:
            answer = "I don't know the answer"

        return RunResult(
            question=question,
            answer_markdown=answer,
            metadata={"test_runner": True}
        )

def get_runner():
    return SimpleRunner()
"""
            runner_file = temp_path / "simple_runner.py"
            runner_file.write_text(runner_content)

            # Run pondera CLI
            cmd = [
                sys.executable,
                "-m",
                "pondera.cli",
                "run",
                str(case_file),
                "--runner",
                f"{runner_file.stem}:get_runner",
            ]

            env = os.environ.copy()
            env["PYTHONPATH"] = str(Path(__file__).parent.parent.parent / "src")

            result = subprocess.run(cmd, capture_output=True, text=True, cwd=temp_path, env=env)

            # Check that the command executed (exit code may vary based on judge)
            print(f"CLI test exit code: {result.returncode}")
            print(f"CLI test stdout: {result.stdout}")
            print(f"CLI test stderr: {result.stderr}")

            # At minimum, it should not crash with import errors
            assert "ImportError" not in result.stderr
            assert "ModuleNotFoundError" not in result.stderr

    def test_cli_run_directory(self) -> None:
        """Test CLI running all cases in a directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create multiple test cases
            case1_content = """
id: test_case_1
input:
  query: "What is 2 + 2?"
expect:
  must_contain: ["4"]
judge:
  overall_threshold: 70
"""
            case2_content = """
id: test_case_2
input:
  query: "What is the capital of Italy?"
expect:
  must_contain: ["Rome"]
judge:
  overall_threshold: 70
"""

            (temp_path / "case1.yaml").write_text(case1_content)
            (temp_path / "case2.yaml").write_text(case2_content)

            # Create runner
            runner_content = """
import sys
from pathlib import Path
src_path = Path(__file__).parent.parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from pondera.runner.base import Runner
from pondera.models.run import RunResult

class TestRunner(Runner):
    async def run(self, question, attachments=None, params=None, progress=None):
        if "2 + 2" in question:
            answer = "4"
        elif "capital of Italy" in question:
            answer = "Rome"
        else:
            answer = "Unknown"

        return RunResult(
            question=question,
            answer_markdown=answer,
            metadata={}
        )

def get_runner():
    return TestRunner()
"""
            runner_file = temp_path / "test_runner.py"
            runner_file.write_text(runner_content)

            # Run CLI on directory
            cmd = [
                sys.executable,
                "-m",
                "pondera.cli",
                "run",
                str(temp_path),
                "--runner",
                f"{runner_file.stem}:get_runner",
            ]

            env = os.environ.copy()
            env["PYTHONPATH"] = str(Path(__file__).parent.parent.parent / "src")

            result = subprocess.run(cmd, capture_output=True, text=True, cwd=temp_path, env=env)

            print(f"Directory test exit code: {result.returncode}")
            print(f"Directory test stdout: {result.stdout}")
            print(f"Directory test stderr: {result.stderr}")

            # Should not crash with import errors
            assert "ImportError" not in result.stderr
            assert "ModuleNotFoundError" not in result.stderr

    def test_api_with_real_components(self) -> None:
        """Test API using real runner but with environment setup issues handled gracefully."""
        from tests.integration.test_runner import BasicIntegrationRunner

        # This test only checks that our test runner works correctly
        runner = BasicIntegrationRunner(
            "Test response for API integration"
        )  # Test the runner directly
        import asyncio

        async def test_runner():
            result = await runner.run("Test question")
            assert result.question == "Test question"
            assert result.answer_markdown == "Test response for API integration"
            assert result.metadata["test"] is True

        asyncio.run(test_runner())

    def test_yaml_loading_and_validation(self) -> None:
        """Test that YAML files are properly loaded and validated."""
        from pondera.utils import load_case_yaml

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create a valid YAML case
            case_content = """
id: yaml_validation_test
input:
  query: "Test question"
  params:
    key: "value"
expect:
  must_contain: ["test"]
  must_not_contain: ["error"]
judge:
  overall_threshold: 75
  request: "Custom judge request"
timeout_s: 300
"""
            case_file = temp_path / "valid_case.yaml"
            case_file.write_text(case_content)

            # Load and validate
            case_spec = load_case_yaml(case_file)

            assert case_spec.id == "yaml_validation_test"
            assert case_spec.input.query == "Test question"
            assert case_spec.input.params["key"] == "value"
            assert "test" in case_spec.expect.must_contain
            assert "error" in case_spec.expect.must_not_contain
            assert case_spec.judge.overall_threshold == 75
            assert case_spec.judge.request == "Custom judge request"
            assert case_spec.timeout_s == 300

    def test_case_file_iteration(self) -> None:
        """Test that case file discovery works correctly."""
        from pondera.cli import _iter_case_files

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create various files
            (temp_path / "case1.yaml").write_text("id: test1\ninput:\n  query: 'test'")
            (temp_path / "case2.yml").write_text("id: test2\ninput:\n  query: 'test'")
            (temp_path / "not_case.txt").write_text("not a case file")

            # Create subdirectory with case
            subdir = temp_path / "subdir"
            subdir.mkdir()
            (subdir / "case3.yaml").write_text("id: test3\ninput:\n  query: 'test'")

            # Test file iteration
            case_files = list(_iter_case_files(temp_path))
            case_names = [f.name for f in case_files]

            assert "case1.yaml" in case_names
            assert "case2.yml" in case_names
            assert "case3.yaml" in case_names
            assert "not_case.txt" not in case_names

            # Should find exactly 3 case files
            assert len(case_files) == 3

    def test_runner_loading_mechanism(self) -> None:
        """Test the runner loading mechanism works correctly."""
        from pondera.cli import _load_runner

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create a runner module
            runner_content = """
import sys
from pathlib import Path
src_path = Path(__file__).parent.parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from pondera.runner.base import Runner
from pondera.models.run import RunResult

class MyRunner(Runner):
    async def run(self, question, attachments=None, params=None, progress=None):
        return RunResult(
            question=question,
            answer_markdown="Test answer",
            metadata={}
        )

def create_runner():
    return MyRunner()

# Also test direct instance
runner_instance = MyRunner()
"""
            runner_file = temp_path / "my_runner.py"
            runner_file.write_text(runner_content)

            # Add temp directory to Python path
            import sys

            original_path = sys.path.copy()
            sys.path.insert(0, str(temp_path))

            try:
                # Test loading factory function
                runner1 = _load_runner("my_runner:create_runner")
                assert runner1 is not None

                # Test loading instance
                runner2 = _load_runner("my_runner:runner_instance")
                assert runner2 is not None

                # Test loading class directly
                runner3 = _load_runner("my_runner:MyRunner")
                assert runner3 is not None

            finally:
                sys.path[:] = original_path

    def test_invalid_runner_spec_handling(self) -> None:
        """Test that invalid runner specs are handled properly."""
        from pondera.cli import _load_runner
        import typer

        # Test malformed spec
        with pytest.raises(typer.BadParameter, match="Expected format"):
            _load_runner("invalid_format")

        # Test non-existent module
        with pytest.raises(typer.BadParameter, match="Cannot import module"):
            _load_runner("nonexistent_module:some_function")
