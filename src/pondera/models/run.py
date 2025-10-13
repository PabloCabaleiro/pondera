from typing import Any

from pydantic import BaseModel, Field, ConfigDict

# ─────────────────────────────────────────────────────────────────────────────
# Runner output (what the runner must return)
# ─────────────────────────────────────────────────────────────────────────────


class RunResult(BaseModel):
    """
    Standardized runner output. The judge consumes `answer`.
    """

    model_config = ConfigDict(extra="forbid")

    question: str
    answer: str = Field(default="")
    # absolute or relative paths to generated files (optional)
    artifacts: list[str] = Field(default_factory=list)
    # explicit list of files to be passed to the judge (superset or curated subset of artifacts)
    files: list[str] = Field(default_factory=list)
    # any useful metadata (steps, timings, costs, tool usage, etc.)
    metadata: dict[str, Any] = Field(default_factory=dict)
    # error details if runner failed (exception type and message)
    error: str | None = Field(default=None)

    def __str__(self) -> str:  # pragma: no cover - trivial
        meta_keys = sorted(self.metadata.keys())
        return (
            f"RunResult(len(answer)={len(self.answer)}, artifacts={len(self.artifacts)}, "
            f"files={len(self.files)}, metadata_keys={meta_keys})"
        )

    def __repr__(self) -> str:  # pragma: no cover - trivial
        return (
            "RunResult(question="
            + repr(self.question[:40] + ("…" if len(self.question) > 40 else ""))
            + f", answer_len={len(self.answer)}, artifacts={self.artifacts}, files={self.files}, "
            f"metadata_keys={list(self.metadata.keys())})"
        )
