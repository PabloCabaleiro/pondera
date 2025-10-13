# Pondera



Lightweight, YAML‑first evaluation for AI models and agents. You write cases in YAML, provide a tiny async runner that returns markdown, and get a strict rubric‑scored JSON judgment back. No framework lock‑in.

## Why Pondera?

- Single source of truth (YAML).
- Any model/provider (you control inference).
- Strict JSON judgment schema with weighted rubric scoring.
- Simple Python API (CLI removed).
- Reproducible artifacts (answer, judgment, summary, meta). Per‑case rubric overrides.

## Core Concepts

### Case (YAML)

Defines one evaluation: query, optional attachments, expectations, thresholds, optional per‑case rubric.

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

Rich example with rubric override:

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


- **Runner (you)**: produces an answer markdown given the case input. Must implement:

```python
class Runner(Protocol):
    async def run(self, *, question: str, attachments: list[str] | None = None,
                  params: dict[str, Any] | None = None, progress: ProgressCallback | None = None) -> RunResult: ...
```

- **Judge (built-in default)**: the bundled class `Judge` (import with `from pondera.judge import Judge`) scores with a rubric and returns a strict `Judgment`. It is the default expectation. You can override it by passing any object matching `JudgeProtocol` (async `judge(...) -> Judgment`). Custom example:

```python
from pondera.judge import JudgeProtocol
from pondera.models.judgment import Judgment

class ConstantJudge(JudgeProtocol):
  async def judge(self, *, question: str, answer: str, files, judge_request: str,
          rubric=None, system_append: str = "") -> Judgment:
    return Judgment(
      score=100,
      evaluation_passed=True,
      reasoning="Always passes (demo)",
      criteria_scores={c.name: 100 for c in (rubric or [])} if rubric else {"overall": 100},
      issues=[],
      suggestions=["This is a placeholder judge"],
    )

# use: evaluate_case(..., judge=ConstantJudge())
```

## Install

```bash
# Using uv (recommended)
uv add 'git+ssh://git@github.com/PabloCabaleiro/pondera.git@v0.6.0'
# or from source in editable mode
uv pip install 'git+ssh://git@github.com/PabloCabaleiro/pondera.git@v0.6.0'
```

The judge uses the pydantic-ai ecosystem. Configure provider credentials via env vars (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `AZURE_OPENAI_API_KEY`, etc.) plus optional `PONDERA_` settings.

## Usage

### Python API


`evaluate_case_async` is the real coroutine that performs the evaluation (single or multi‑repetition). Use it inside async code (`await evaluate_case_async(...)`).

`evaluate_case` is a thin convenience wrapper for synchronous contexts: it calls `asyncio.run` on `evaluate_case_async` and raises if an event loop is already running (to prevent nested loop issues).

Return type is always `MultiEvaluationResult` for a stable downstream API. When repetitions == 1 the object contains exactly one `EvaluationResult` in `evaluations[0]` and aggregates are computed over that single sample.

```python
from pondera.api import evaluate_case
from pondera.judge import Judge

class DemoRunner:
  async def run(self, *, question, attachments=None, params=None, progress=None):
    from pondera.models.run import RunResult
    return RunResult(question=question, answer=f"# Answer\n\nEcho: **{question}**\n")

multi = evaluate_case("eval/cases/hello.yaml", runner=DemoRunner(), judge=Judge())
single = multi.evaluations[0]
print(multi.passed, single.judgment.score)
```

### Testing (pytest)

```python
from pondera.api import evaluate_case
from pondera.judge import Judge

def test_hello_case():
  class DemoRunner:
    async def run(self, *, question, attachments=None, params=None, progress=None):
      from pondera.models.run import RunResult
      return RunResult(question=question, answer=f"Answer: {question}")
  multi = evaluate_case("eval/cases/hello.yaml", runner=DemoRunner(), judge=Judge())
  assert multi.passed
  assert multi.evaluations[0].judgment is not None
```

See `docs/TESTING.md` for markers and commands.

## Quickstart

1. Install: `uv add pondera`
2. Write a case YAML under `eval/cases/`
3. Implement a runner with `async run(...)-> {"answer": str}`
4. Call `evaluate_case(path, runner=RunnerImpl(), judge=Judge())`
5. Use `multi.evaluations[0]` for single runs or iterate for reproducibility studies



## Artifacts

**Per case directory** (if you persist):

- `answer.md` (model's answer)
- `judgment.json` (judgment schema)
- `judge_prompt.txt` (raw prompt sent to the judge, including any inlined file snippets; only created when non‑empty)
- `meta.json` (thresholds, timings, pass flag, runner metadata)
- `summary.md` (human readable summary)

**Multi evaluation**:

- Aggregated stats (min / max / mean / median / stdev / variance) per criterion + overall inside `multi/aggregates.json` with a human summary.

## Environment & Settings

Settings model: `pondera.settings.PonderaSettings` (env prefix `PONDERA_`). Key fields:

- `PONDERA_ARTIFACTS_DIR`: (default eval/artifacts)
- `MODEL_FAMILY`: (e.g. openai | anthropic | azure | ollama | bedrock)
- `MODEL_TIMEOUT`: default 120
- Provider model name vars (`OPENAI_MODEL_NAME`, `AZURE_MODEL_NAME`, `OLLAMA_MODEL_NAME`, `BEDROCK_MODEL_NAME`, etc.) and credentials.

Example (OpenAI):

```bash
export PONDERA_MODEL_FAMILY=openai
export OPENAI_API_KEY=sk-...
export PONDERA_OPENAI_MODEL_NAME=gpt-4o-mini
```

Similar patterns: anthropic (`ANTHROPIC_API_KEY` + `MODEL_FAMILY`=anthropic), azure (`AZURE_OPENAI_*` env vars + `MODEL_FAMILY`=azure), ollama (`OLLAMA_URL` + `MODEL_FAMILY`=ollama), bedrock (AWS credentials + `MODEL_FAMILY`=bedrock).

### .env Template

Create a `.env` file in your project root (values below are examples):

```bash
# Core
MODEL_FAMILY=azure            # azure | openai | ollama | bedrock | anthropic
MODEL_TIMEOUT=120             # seconds
VDB_EMBEDDINGS_MODEL_FAMILY=azure

# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://your_endpoint.openai.azure.com
AZURE_OPENAI_API_VERSION=2024-06-01
AZURE_OPENAI_API_KEY=your_secret_key
AZURE_MODEL_NAME=gpt-4o
AZURE_OPENAI_DEPLOYMENT=gpt-4o
AZURE_VDB_EMBEDDINGS_MODEL_NAME=text-embedding-3-small

# OpenAI
OPENAI_API_KEY=openai_api_key
OPENAI_MODEL_NAME=gpt-4.5-preview
OPENAI_VDB_EMBEDDINGS_MODEL_NAME=text-embedding-3-small

# Ollama (local)
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL_NAME=llama3.2:3b-instruct-fp16
OLLAMA_VDB_EMBEDDINGS_MODEL_NAME=snowflake-arctic-embed2:latest

# Bedrock (example)
AWS_REGION=us-east-1
BEDROCK_MODEL_NAME=anthropic.claude-3-sonnet-20240229-v1:0

# Anthropic
ANTHROPIC_API_KEY=your_anthropic_key
```

Guidance: set `MODEL_FAMILY`, supply the matching provider credentials + model name(s), adjust `MODEL_TIMEOUT` as needed. Embeddings variables optional unless you use vector DB functionality.

## Limitations

- Artifacts from the runners are just read as plain text and the content provided to the judge up to 20 KB per file.
- No pypi package yet.
- No CI/CD.

## Contributing

Open issues for runner/judge adapters, schema tweaks, or export needs. PRs welcome (keep them small and tested). License: MIT.
