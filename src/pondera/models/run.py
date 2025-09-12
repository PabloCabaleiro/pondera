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
