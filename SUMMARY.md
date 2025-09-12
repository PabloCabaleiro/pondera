# Summary

Pondera evaluates model or agent outputs against YAML-defined cases. A case specifies the query, optional attachments, expectations (simple textual checks), and judge configuration (rubric, thresholds).

## Flow

1. Runner produces an answer (and optional artifacts/files)
2. Judge scores with rubric -> EvaluationResult (with thresholds & pre-checks)
3. MultiEvaluationResult aggregates repetitions.
4. Artifacts persisted per case: `answer.md`, `judgment.json`, `judge_prompt.txt` (raw prompt when available), `meta.json` (thresholds, timings, pass, has_judge_prompt), `summary.md`.
5. Multi evaluations add a multi/ directory with per‑repetition subfolders and aggregate stats.

## Extensibility

- Provide a custom Runner (async run method) or a custom Judge (implements JudgeProtocol).
- Rubric can be overridden per case.
- Settings (env-driven) control artifact directory and model backend.
