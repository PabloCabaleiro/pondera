# Pondera

Pondera is a lightweight, YAML-first framework to evaluate AI models and agents with pluggable runners and an LLM-as-a-judge. It keeps test cases in YAML, runs your model (however you ship it), and scores outputs against a rubric—no tight coupling to any specific stack.

## Why Pondera?

- **YAML as single source of truth** – All test inputs & expectations live in YAML files (decoupled from code).
- **Model-agnostic** – Evaluate Python callables, HTTP services, or anything else via runners.
- **Typed judging** – LLM judge returns a strict Judgment schema (Pydantic).
- **MCP-ready judge** – Optional MCP tools/resources available to the judge (configurable & allow-listed).
- **Portable** – Use the CLI, a tiny Python API, or a pytest helper (pytest is optional).
- **Reproducible** – Standard artifacts (answer.md, judgment.json, summary.md, meta.json) per case.

## Core Concepts

- **Case (YAML)**: Defines the input (query, attachments, params), pre-judge expectations, judge request, rubric overrides, thresholds, and optional MCP config.
- **Runner**: Contract about how to obtain the answer being evaluated (e.g., a Python function, an HTTP endpoint). Returns a standard RunResult.
- **Judge**: Scores the answer according to a rubric and returns a structured Judgment (overall score, per-criterion scores, issues, suggestions).

## High-Level YAML Shape (for context)

> *Full spec will be documented; this is indicative.

```yaml
id: unique_case_id
input:
  query: "User question or instruction"
  attachments: []            # optional local file paths
  params: {}                 # free-form dict for runner
expect:
  must_contain: []
  must_not_contain: []
  regex_must_match: []
judge:
  request: "How to evaluate this answer"
  overall_threshold: 70
  per_criterion_thresholds: { correctness: 70, completeness: 60 }
  rubric:                    # optional per-case override of default rubric
    - name: correctness
      weight: 0.4
      description: "Facts are accurate; no hallucinations."
  model: null                # optional judge model override
  mcp:                       # optional (judge-side) MCP config
    servers: []              # list of MCP endpoints
    tools_allowlist: []      # which tools the judge may use
    context: {}              # resource/context hints
timeout_s: 240
```

## Roadmap

### v0.1 — MVP

- [ ] **Schemas**: `CaseSpec`, `RubricCriterion`/`Rubric`, `RunResult`, `Judgment`.
- [ ] **Runners**: `PythonCallableRunner`.
- [ ] **Judge**: `PydanticAIJudge` (typed JSON result, model-agnostic).
- [ ] **API**: `evaluate_case(...)` (sync wrapper calling async core).
- [ ] **CLI**: `pondera run <cases_dir> --runner ... --artifacts ....`
- [ ] **Pytest helper**: `load_cases()`, `run_case()`; sample test file using parametrize.
- [ ] **Artifacts**: `answer.md`, `judgment.json`, `summary.md`, `meta.json`.
- [ ] **Docs**: README, YAML schema reference, quickstart examples.

### Backlog

- [ ] **Runners**: `HTTPRunner`, `CLIRunner`, `NotebookRunner` (Jupyter/nbclient)...

- [ ] **MCP (judge-side)**: config pass-through.

- [ ] **Judging**: Multi-judge aggregation (mean/median/majority), caching by case hash.

- [ ] **Config**: Project-level defaults (pondera.yaml), env/secret injection.

- [ ] **Concurrency & timeouts**: global + per-case; graceful retries.

- [ ] **Progress hooks**: optional progress(line) for runners & judge.

- [ ] **Enhanced logging**: structured logs; cost/token usage capture (if available).

- [ ] **Exports**: CSV/JSONL summaries for dashboards; simple HTML report.

- [ ] **Pytest plugin** (auto-collect YAML cases via flags).

## Getting Involved

- **Issues / Ideas**: Propose runner/judge adapters, schema tweaks, or MCP use-cases.
- **Contributions**: PRs welcome once the v0.1 schema stabilizes (tests + docs).
- **License**: MIT (proposed; confirm before first release).
