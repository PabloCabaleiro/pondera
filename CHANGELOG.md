# Pondera Changelog

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## WIP

- [ ] Remove duplicate settings, e.g: `judge_model`, `default_model`
- [ ] Add Protocol to class Judge in case someone wants to override it.
- [ ] Improve results message.
- [ ] Update readme.
- [ ] Removing cli for now.
- [ ] Fixing artfacts report for api.


## v0.1.0

### Added

- **Model agnostic**: improved the agents module to support different models using PydanticAI.
- **Judging**: Multi-judge aggregation (mean/median/majority), caching by case hash.
- **Propagating artifacts**: Propagating runner artifacts to the Judge.

## v0.1.0 — MVP

### Added

- **Schemas**: `CaseSpec`, `RubricCriterion`/`Rubric`, `RunResult`, `Judgment`.
- **Judge**: `Judge` (typed JSON result, model-agnostic).
- **API**: `evaluate_case(...)` (sync wrapper calling async core).
- **CLI**: `pondera run <cases_dir> --runner ... --artifacts ....`
- **Pytest helper**: `load_cases()`, `run_case()`; sample test file using parametrize.
- **Artifacts**: `answer.md`, `judgment.json`, `summary.md`, `meta.json`.
- **Docs**: README, YAML schema reference, quickstart examples.
- **Tests**: Adding basic tests.
