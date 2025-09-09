# Pondera

Pondera is a lightweight, YAML-first framework to evaluate AI models and agents with pluggable runners and an LLM-as-a-judge. It keeps test cases in YAML, runs your model (however you ship it), and scores outputs against a rubric—no tight coupling to any specific stack.

## Why Pondera?

YAML single source of truth for inputs & expectations. Model/provider agnostic: you supply a runner (any callable that can produce markdown). Judge returns a strict JSON schema (Judgment) with weighted rubric scoring. Portable via CLI or small Python API. Reproducible artifacts per case (answer, judgment, summary, meta). Minimal defaults; you can override rubric per case.

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
from pondera.judge.pydantic_ai import Judge

class DemoRunner:
    async def run(self, *, question, attachments=None, params=None, progress=None):
        return {"answer_markdown": f"# Answer\n\nEcho: **{question}**\n"}

res = evaluate_case("eval/cases/hello.yaml", runner=DemoRunner(), judge=Judge())
print(res.passed, res.judgment.score)
```

### 3. Testing (pytest)

```python
from pondera.api import evaluate_case
from pondera.judge.pydantic_ai import LlmJudge

def test_hello_case():
  class DemoRunner:
    async def run(self, *, question, attachments=None, params=None, progress=None):
      return {"answer_markdown": f"Answer: {question}"}
  res = evaluate_case("eval/cases/hello.yaml", runner=DemoRunner(), judge=Judge())
  assert res.passed
```

See `docs/TESTING.md` for markers and commands.

## Quickstart

1. Install: `uv add pondera`
2. Create a case YAML (e.g. `eval/cases/hello.yaml`)
3. Write a small runner class or factory with an async `run` returning `answer_markdown`
4. Run: `pondera run eval/cases --runner mypkg.runner_factory:make_runner --artifacts eval/artifacts`
5. Inspect artifacts under `eval/artifacts/<case_id>/`

## YAML Schema (concise)

Required top-level fields: `id`, `input.query`.
Input: `query: str`, optional `attachments: [paths]`, `params: {free-form}`.
Expect (all optional lists): `must_contain`, `must_not_contain`, `regex_must_match`.
Judge: `request` (instructions for judge), `overall_threshold` (default 70), `per_criterion_thresholds` (dict), optional `rubric` (list of {name, weight, description}), `model` (override), `system_append` (extra system guidance).
Timeout: `timeout_s` (default 240).
Repetitions: `repetitions` (default 1) – if >1, you can call the multi API to measure reproducibility.

## Artifacts

Per case directory (slugified id):
answer.md (raw markdown answer)
judgment.json (typed judge output)
meta.json (pass/fail, thresholds, timings, runner metadata)
summary.md (human readable scores + issues/suggestions)

For repeated runs (multi evaluation) you can programmatically gather all run artifacts and aggregated statistics (min/mean/median/max/stdev/variance) via `evaluate_case_multi` / `evaluate_case_multi_async`.

## Environment & Settings

Settings model: `pondera.settings.PonderaSettings` (env prefix `PONDERA_`, `.env` supported). Key fields:
PONDERA_ARTIFACTS_DIR (default eval/artifacts)
PONDERA_TIMEOUT_DEFAULT_S (default 240)
PONDERA_JUDGE_MODEL (planned default identifier; current judge path uses provider family vars below)
Model provider selection uses generic fields: set `PONDERA_MODEL_FAMILY` and the corresponding model name + API key, e.g. for OpenAI:

```bash
export PONDERA_MODEL_FAMILY=openai
export OPENAI_API_KEY=sk-...
export PONDERA_OPENAI_MODEL_NAME=gpt-4o-mini
```

Similar patterns: anthropic (ANTHROPIC_API_KEY, PONDERA_MODEL_FAMILY=anthropic), azure (AZURE_OPENAI_* plus PONDERA_MODEL_FAMILY=azure), etc.

## Limitations / Notes

Single judge only (no aggregation). Built-in generic runners not yet included (write a tiny custom runner). Pytest helper from earlier roadmap not yet implemented. Multi-judge, runner templates, export formats are roadmap items.

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

## Roadmap (abridged)

v0.1 (current): core schemas, single judge, CLI, API, artifacts, basic tests.
v0.2: multi-judge aggregation, runner artifact propagation, reproducibility (multi evaluation) support.
Backlog: built-in runners (callable/http/cli/notebook), config file, export formats (CSV/JSONL/HTML), pytest plugin, MCP enhancements.

## Getting Involved

Open issues for runner/judge adapters, schema refinements, or export needs. PRs welcome (keep changes small and tested). License: MIT.
