# src/pondera/runner/base.py

from typing import Any, Awaitable, Callable, Protocol

from pondera.models.run import RunResult

# Async progress callback contract (optional)
ProgressCallback = Callable[[str], Awaitable[None]]


class RunnerError(RuntimeError):
    """Raised when a runner cannot execute or normalize the result."""


class Runner(Protocol):
    """
    Minimal contract for a Pondera runner.

    Implementations should:
        - Use the provided inputs (question, attachments, params) as needed.
        - Use the progress callback for streaming status (optional).
        - Return a RunResult (or a dict normalizable to RunResult).
    """

    async def run(
        self,
        *,
        question: str,
        attachments: list[str] | None = None,
        params: dict[str, Any] | None = None,
        progress: ProgressCallback | None = None,
    ) -> RunResult: ...


async def emit_progress(progress: ProgressCallback | None, line: str) -> None:
    """
    Best-effort progress emission. Never raises into the runner.
    """
    if progress is None:
        return
    try:
        await progress(line)
    except Exception:
        # Progress should never break the run.
        pass


def normalize_run_result(result: Any, *, question: str) -> RunResult:
    """
    Normalize user runner outputs to a RunResult.

    Accepted:
        - RunResult
        - dict with keys compatible with RunResult ('answer_markdown' required)

    Injects the 'question' into the dict if missing.
    """
    if isinstance(result, RunResult):
        return result

    if isinstance(result, dict):
        data: dict[str, Any] = {"question": question, **result}
        try:
            return RunResult.model_validate(data)
        except Exception as e:
            raise RunnerError(f"Could not coerce dict result to RunResult: {e}") from e

    raise RunnerError(
        f"Unsupported runner return type {type(result)!r}. "
        "Return a RunResult or a dict with 'answer_markdown' (and optional 'artifacts', 'metadata')."
    )
