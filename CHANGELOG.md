# Changelog

The format follows the principles of [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) and uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased](https://github.com/PabloCabaleiro/pondera/tree/main)

### Added (Unreleased)

- Persist judge prompt as `judge_prompt.txt` and include `judge_prompt` field in `Judgment` plus `has_judge_prompt` flag in `meta.json`.

### Changed (Unreleased)

- API now always returns `MultiEvaluationResult` (single run wrapped with one `EvaluationResult`) for a stable schema.

### Fixed (Unreleased)

- Updated tests to align with unified return type.

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
