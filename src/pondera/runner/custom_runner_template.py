# examples/custom_runner_template.py

from typing import Any

from pondera.models.run import RunResult
from pondera.runner.base import emit_progress, normalize_run_result, RunnerError


# Example async runner users can adapt
async def my_runner(
    *,
    question: str,
    attachments: list[str] | None = None,
    params: dict[str, Any] | None = None,
    progress: Any = None,
) -> RunResult:
    attachments = attachments or []
    params = params or {}

    await emit_progress(progress, "runner: starting…")

    # ... do your work here (call your agent, HTTP service, etc.) ...
    try:
        answer_md = f"# Answer\n\nQuestion: **{question}**\n\nParams: `{params}`\n"
    except Exception as ex:
        raise RunnerError(f"runner: execution failed: {ex}") from ex

    await emit_progress(progress, "runner: preparing result…")

    # Return RunResult or a dict normalizable to it
    return normalize_run_result(
        {
            "answer": answer_md,
            "artifacts": [],  # optional file paths/URIs
            "files": [],  # list of files to expose to judge (subset/superset of artifacts)
            "metadata": {"steps": 1},  # optional info
        },
        question=question,
    )
