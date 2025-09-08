"""Test runners for integration tests."""

from typing import Any

from pondera.runner.base import Runner, ProgressCallback
from pondera.models.run import RunResult


class BasicIntegrationRunner(Runner):
    """Simple test runner that returns predictable responses."""

    def __init__(self, response: str = "This is a test response"):
        self.response = response

    async def run(
        self,
        question: str,
        attachments: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        progress: ProgressCallback | None = None,
    ) -> RunResult:
        """Return a simple test response."""
        return RunResult(
            question=question,
            answer_markdown=self.response,
            metadata={"test": True, "params": params or {}},
        )


class MathRunner(Runner):
    """Test runner that can solve simple math problems."""

    async def run(
        self,
        question: str,
        attachments: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        progress: ProgressCallback | None = None,
    ) -> RunResult:
        """Solve simple math problems."""
        # Simple math solver for testing
        if "2 + 2" in question:
            answer = "4"
        elif "3 * 3" in question:
            answer = "9"
        elif "10 / 2" in question:
            answer = "5"
        else:
            answer = "I can only solve simple arithmetic problems like 2+2, 3*3, or 10/2"

        return RunResult(
            question=question,
            answer_markdown=answer,
            metadata={"solver": "simple_math", "params": params or {}},
        )


def get_test_runner() -> Runner:
    """Factory function to get a test runner."""
    return BasicIntegrationRunner()


def get_math_runner() -> Runner:
    """Factory function to get a math test runner."""
    return MathRunner()


# Backward compatibility aliases
TestRunner = BasicIntegrationRunner
MathTestRunner = MathRunner
