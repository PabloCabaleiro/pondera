from __future__ import annotations

import json
import re
from pathlib import Path
import logging

from pondera.models.evaluation import EvaluationResult
from pondera.models.multi_evaluation import MultiEvaluationResult


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
    (case_dir / "answer.md").write_text(res.run.answer or "", encoding="utf-8")

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

    # summary.md (human friendly) + log to stdout via logger
    summary_text = _summary_md(res)
    (case_dir / "summary.md").write_text(summary_text, encoding="utf-8")
    logging.getLogger("pondera.artifacts").info("\n" + summary_text.rstrip())

    return case_dir


def write_multi_evaluation_artifacts(
    artifacts_root: Path | str, res: MultiEvaluationResult
) -> Path:
    """Write artifacts for a multi-evaluation result.

    Layout:
      <root>/<case-slug>/multi/
        summary.md               (aggregate human readable)
        aggregates.json          (raw aggregates + pass + primary metric)
        evaluations/<idx>/...    (each repetition, reuse write_case_artifacts)
    """
    root = Path(artifacts_root)
    base = root / _slug(res.case_id) / "multi"
    evals_dir = base / "evaluations"
    evals_dir.mkdir(parents=True, exist_ok=True)

    # Per evaluation artifacts (numbered for reproducibility, preserve order)
    for idx, ev in enumerate(res.evaluations, start=1):
        write_case_artifacts(evals_dir / f"{idx:03d}", ev)

    # Aggregates json
    aggregates_payload = {
        "case_id": res.case_id,
        "passed": res.passed,
        "primary_metric": res.primary_metric.value,
        "overall": res.aggregates.overall.model_dump(),
        "per_criterion": {k: v.model_dump() for k, v in res.aggregates.per_criterion.items()},
    }
    (base / "aggregates.json").write_text(
        json.dumps(aggregates_payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # Human summary
    lines: list[str] = []
    lines.append(f"# Multi Evaluation: {res.case_id}")
    lines.append("")
    lines.append(f"- **Repetitions**: {len(res.evaluations)}")
    lines.append(f"- **Primary metric**: {res.primary_metric.value}")
    lines.append(f"- **Passed**: {'✅' if res.passed else '❌'}")
    ov = res.aggregates.overall
    lines.append(
        f"- **Overall**: min={ov.min}, max={ov.max}, mean={ov.mean}, median={ov.median}, stdev={ov.stdev}, variance={ov.variance}"
    )
    if res.aggregates.per_criterion:
        lines.append("\n## Per-criterion aggregates")
        for k, agg in sorted(res.aggregates.per_criterion.items()):
            lines.append(
                f"- **{k}**: min={agg.min}, max={agg.max}, mean={agg.mean}, median={agg.median}, stdev={agg.stdev}, variance={agg.variance}"
            )
    multi_summary = "\n".join(lines) + "\n"
    (base / "summary.md").write_text(multi_summary, encoding="utf-8")
    logging.getLogger("pondera.artifacts").info("\n" + multi_summary.rstrip())

    return base
