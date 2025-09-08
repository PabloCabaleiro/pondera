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

### Case (YAML)

The single source of truth for a test (query, attachments, expectations, judge config).

Minimal example:

```yaml
id: hello
input:
  query: "What is the SRY gene?"
expect:
  must_contain: ["SRY", "sex-determining"]
judge:
  request: "Evaluate correctness and clarity."
  overall_threshold: 75
timeout_s: 120
```

Rich example with rubric override

```yaml
id: genes_per_chr
input:
  query: "Give me a plot with the number of genes per chromosome"
  params:
    mode: "explain+code"
expect:
  must_contain: ["genes per chromosome", "plot"]
  regex_must_match: ["(?i)steps?:", "(?i)reproduce|reproduc"]
judge:
  request: |
    Judge whether the answer produces (or clearly describes how to produce)
    a valid plot of the number of genes per chromosome. Penalize vague steps.
  overall_threshold: 70
  per_criterion_thresholds:
    correctness: 70
    completeness: 60
  rubric:
    - name: correctness
      weight: 0.4
      description: Facts are accurate; no hallucinations.
    - name: completeness
      weight: 0.3
      description: Covers the task end-to-end with necessary detail.
    - name: methodology_repro
      weight: 0.2
      description: Steps clear enough to reproduce.
    - name: presentation
      weight: 0.1
      description: Clear structure and formatting.
timeout_s: 240
```


- **Runner (you)**: how to obtain an answer given the case input. Must implement:

```python
class Runner(Protocol):
    async def run(self, *, question: str, attachments: list[str] | None = None,
                  params: dict[str, Any] | None = None, progress: ProgressCallback | None = None) -> RunResult: ...
```

- **Judge (Pondera)**: scores the answer with a rubric and returns a strict Judgment.

## Install

```bash
# Using uv (recommended)
uv add pondera
# or from source in editable mode
uv pip install -e .
```

!!! The judge uses the pydantic-ai ecosystem. Configure your provider creds via env (e.g., OPENAI_API_KEY) or via PONDERA_… variables (see Settings).

## Usage

### 1. CLI

```bash
pondera run eval/cases \
  --runner myproj.eval_targets:make_runner \
  --artifacts eval/artifacts
```

`--runner` accepts `module:object` where object is a factory, a class, or an instance with run(...).

Artifacts are written under `<artifacts>/<case_id>/`.

### 2. Python API

```python
from pondera.api import evaluate_case
from pondera.judge.pydantic_ai import PydanticAIJudge

class DemoRunner:
    async def run(self, *, question, attachments=None, params=None, progress=None):
        return {"answer_markdown": f"# Answer\n\nEcho: **{question}**\n"}

res = evaluate_case("eval/cases/hello.yaml", runner=DemoRunner(), judge=PydanticAIJudge())
print(res.passed, res.judgment.score)
```

### 3. Pytest helper

```python
from pondera.pytest_helpers import load_cases, run_case
from pondera.judge.pydantic_ai import PydanticAIJudge

CASES = load_cases("eval/cases")

def test_cases():
    judge = PydanticAIJudge()
    for case in CASES:
        res = run_case(case, runner=DemoRunner(), judge=judge)
        assert res.passed
```

## Settings

Centralized via `pondera.settings.PonderaSettings` (env prefix `PONDERA_`, `.env` supported):

- `PONDERA_JUDGE_MODEL` (default: `openai:gpt-4o-mini`)
- `PONDERA_ARTIFACTS_DIR` (default: `eval/artifacts`)
- `PONDERA_TIMEOUT_DEFAULT_S` (default: 240)

Provider creds exported for SDKs/pydantic-ai:

- `OPENAI_API_KEY` (or `PONDERA_OPENAI_API_KEY`)
- `ANTHROPIC_API_KEY`, `AZURE_OPENAI_*`, etc.

```bash
export PONDERA_JUDGE_MODEL="openai:gpt-4o-mini"
export OPENAI_API_KEY="sk-..."
```

## Roadmap

### v0.1 — MVP

- [x] **Schemas**: `CaseSpec`, `RubricCriterion`/`Rubric`, `RunResult`, `Judgment`.
- [x] **Judge**: `PydanticAIJudge` (typed JSON result, model-agnostic).
- [x] **API**: `evaluate_case(...)` (sync wrapper calling async core).
- [x] **CLI**: `pondera run <cases_dir> --runner ... --artifacts ....`
- [x] **Pytest helper**: `load_cases()`, `run_case()`; sample test file using parametrize.
- [x] **Artifacts**: `answer.md`, `judgment.json`, `summary.md`, `meta.json`.
- [x] **Docs**: README, YAML schema reference, quickstart examples.
- [x] **Tests**: Adding basic tests.

### v0.2

- [ ] **Judging**: Multi-judge aggregation (mean/median/majority), caching by case hash.
- [ ] **Propagating artifacts**: Propagating runner artifacts to the Judge.

### Backlog

- [ ] **Built-in Runners**: `PythonCallableRunner`, `HTTPRunner`, `CLIRunner`, `NotebookRunner` (Jupyter/nbclient)...
- [ ] **MCP (judge-side)**: config pass-through.
- [ ] **Config**: Project-level defaults (pondera.yaml), env/secret injection.
- [ ] **Exports**: CSV/JSONL summaries for dashboards; simple HTML report.
- [ ] **Pytest plugin** (auto-collect YAML cases via flags).

## Getting Involved

- **Issues / Ideas**: Propose runner/judge adapters, schema tweaks, or MCP use-cases.
- **Contributions**: PRs welcome once the v0.1 schema stabilizes (tests + docs).
- **License**: MIT (proposed; confirm before first release).
