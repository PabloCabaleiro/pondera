# Changelog

The format follows the principles of [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) and uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased](https://github.com/PabloCabaleiro/pondera/tree/main)

_Nothing yet._

## [v0.3.0](https://github.com/PabloCabaleiro/pondera/releases/tag/v0.3.0) - 2025-09-10

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

### Added

- Model agnostic support via PydanticAI in agents module
- Multi-judge aggregation (mean / median / majority) with case-hash caching
- Propagation of runner artifacts to the Judge

## [v0.1.0](https://github.com/PabloCabaleiro/pondera/releases/tag/v0.1) - 2025-09-08

### Added

- Schemas: `CaseSpec`, `RubricCriterion` / `Rubric`, `RunResult`, `Judgment`
- Judge: typed JSON result, model-agnostic
- API: `evaluate_case(...)` sync wrapper over async core
- CLI: `pondera run <cases_dir> --runner ... --artifacts ...`
- Pytest helpers: `load_cases()`, `run_case()` sample parametrized tests
- Artifacts: `answer.md`, `judgment.json`, `summary.md`, `meta.json`
- Docs: README, YAML schema reference, quickstart examples
- Tests: basic test suite
