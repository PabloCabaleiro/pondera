# Changelog

The format follows the principles of [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) and uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased](https://github.com/PabloCabaleiro/pondera/tree/main)

### Added (Unreleased)

- Persist judge prompt as `judge_prompt.txt` and include `judge_prompt` field in `Judgment` plus `has_judge_prompt` flag in `meta.json`.
- Enforce per-case `timeout_s` via `asyncio.wait_for` around runner and judge execution (raises `asyncio.TimeoutError`).
- Tests for runner and judge timeout behavior.
- Validation: per-criterion threshold keys now validated via Pydantic (`CaseJudge` field validator + `EvaluationResult` model validator) eliminating silent fallback to 0 scores.
- Structured error classes introduced: `RunnerError`, `JudgeError`, `TimeoutError` (subclass of `asyncio.TimeoutError`), and `ValidationError` with wrapping of raw exceptions in runner/judge execution and YAML load path.
- Basic logging: added standard library logging calls (logger name `pondera`) in core API execution path and simple availability test.

### Changed (Unreleased)

- API now always returns `MultiEvaluationResult` (single run wrapped with one `EvaluationResult`) for a stable schema.
- Unified pass/fail logic: removed duplicated threshold code by reusing `compute_pass` for multi-evaluation aggregation.
- Removed ad-hoc runtime threshold key validation function in favor of model-level validators.
- Timeout raising now uses project `TimeoutError` (still an `asyncio.TimeoutError` subclass) for consistent catching.

### Fixed (Unreleased)

- Updated tests to align with unified return type.
- Consistent pass/fail evaluation across single and multi-run cases (previous divergence removed).

## [v0.3.0](https://github.com/PabloCabaleiro/pondera/releases/tag/v0.3.0) - 2025-09-10

<!-- markdownlint-disable-next-line MD024 -->
### Added

- Protocol to `Judge` (allows custom override implementations)

### Changed

- Improved results message
- Updated README
- Removed duplicate settings by consolidating `judge_model` and `default_model`

### Removed

- CLI (temporarily removed; may return later)

### Fixed

- Artifacts report in API (typo: artifacts)

## [v0.2.0](https://github.com/PabloCabaleiro/pondera/releases/tag/v0.2.0) - 2025-09-10

<!-- markdownlint-disable-next-line MD024 -->
### Added

- Model agnostic support via PydanticAI in agents module
- Multi-judge aggregation (mean / median / majority) with case-hash caching
- Propagation of runner artifacts to the Judge

## [v0.1.0](https://github.com/PabloCabaleiro/pondera/releases/tag/v0.1) - 2025-09-08

<!-- markdownlint-disable-next-line MD024 -->
### Added

- Schemas: `CaseSpec`, `RubricCriterion` / `Rubric`, `RunResult`, `Judgment`
- Judge: typed JSON result, model-agnostic
- API: `evaluate_case(...)` sync wrapper over async core
- CLI: `pondera run <cases_dir> --runner ... --artifacts ...`
- Pytest helpers: `load_cases()`, `run_case()` sample parametrized tests
- Artifacts: `answer.md`, `judgment.json`, `summary.md`, `meta.json`
- Docs: README, YAML schema reference, quickstart examples
- Tests: basic test suite
