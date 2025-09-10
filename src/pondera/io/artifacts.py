from __future__ import annotations

import json
import re
from pathlib import Path

from pondera.models.evaluation import EvaluationResult


def _slug(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"[^\w\-]+", "-", s)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s or "case"


def _summary_md(res: EvaluationResult) -> str:
    j = res.judgment
    lines: list[str] = []
    lines.append(f"# Case: {res.case_id}")
    lines.append("")
    lines.append(f"- **Passed**: {'✅' if res.passed else '❌'}")
    lines.append(f"- **Overall score**: {j.score} (threshold ≥ {res.overall_threshold})")
    if res.precheck_failures:
        lines.append(f"- **Pre-checks**: FAILED {len(res.precheck_failures)}")
    else:
        lines.append("- **Pre-checks**: passed")
    if res.timings_s:
        lines.append(
            f"- **Timings**: runner={res.timings_s.get('runner_s', 0):.2f}s, "
            f"judge={res.timings_s.get('judge_s', 0):.2f}s, total={res.timings_s.get('total_s', 0):.2f}s"
        )
    lines.append("")
    lines.append("## Criterion scores")
    for k, v in (j.criteria_scores or {}).items():
        th = res.per_criterion_thresholds.get(k)
        extra = "" if th is None else f" (≥ {th})"
        lines.append(f"- **{k}**: {v}{extra}")
    if j.issues:
        lines.append("\n## Issues")
        for i in j.issues:
            lines.append(f"- {i}")
    if j.suggestions:
        lines.append("\n## Suggestions")
        for s in j.suggestions:
            lines.append(f"- {s}")
    if res.precheck_failures:
        lines.append("\n## Pre-judge check failures")
        for f in res.precheck_failures:
            lines.append(f"- {f}")
    return "\n".join(lines) + "\n"


def write_case_artifacts(artifacts_root: Path | str, res: EvaluationResult) -> Path:
    """
    Write standard artifacts:
      - answer.md
      - judgment.json
      - meta.json
      - summary.md
    Returns the case directory path.
    """
    root = Path(artifacts_root)
    case_dir = root / _slug(res.case_id)
    case_dir.mkdir(parents=True, exist_ok=True)

    # answer.md
    (case_dir / "answer.md").write_text(res.run.answer_markdown or "", encoding="utf-8")

    # judgment.json
    (case_dir / "judgment.json").write_text(
        json.dumps(res.judgment.model_dump(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # meta.json
    meta = {
        "case_id": res.case_id,
        "passed": res.passed,
        "overall_threshold": res.overall_threshold,
        "per_criterion_thresholds": res.per_criterion_thresholds,
        "precheck_failures": res.precheck_failures,
        "timings_s": res.timings_s,
        "runner_metadata": res.run.metadata,
        "artifacts": res.run.artifacts,
        "files": res.run.files,
    }
    (case_dir / "meta.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # summary.md (human friendly)
    (case_dir / "summary.md").write_text(_summary_md(res), encoding="utf-8")

    return case_dir
