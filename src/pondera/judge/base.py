# src/pondera/judge/base.py
from pathlib import Path

from pondera.models.rubric import RubricCriterion
from pondera.models.judgment import Judgment
from pondera.utils import rubric_to_markdown, rubric_weight_note, default_rubric
from pondera.judge.pydantic_ai import get_agent, run_agent
from pondera.judge.protocol import JudgeProtocol
from pondera.errors import JudgeError


class Judge(JudgeProtocol):
    """
    LLM-as-a-judge built on get_agent and run_agent, returning a strict `Judgment`.

    - Model-agnostic: pass any backend id supported by your pydantic_ai setup.
    - Defaults are pulled from Pondera settings.
    - No MCP in MVP (can be added later).
    """

    def __init__(
        self,
        *,
        model: str | None = None,
        rubric: list[RubricCriterion] | None = None,
        system_append: str = "",
    ):
        self._default_rubric = rubric or default_rubric()
        self._system_append = system_append

    async def judge(
        self,
        *,
        question: str,
        answer: str,
        files: list[str] | None,
        judge_request: str,
        rubric: list[RubricCriterion] | None = None,
        system_append: str = "",
    ) -> Judgment:
        rb = rubric or self._default_rubric
        if not rb:
            raise JudgeError("No rubric provided or configured.")

        use_system = self._system_prompt(
            rb,
            self._system_append + (("\n" + system_append) if system_append else ""),
        )

        # Create agent with the specified model and system prompt
        agent = get_agent(system_prompt=use_system, output_type=Judgment)

        files_section = "\n".join(f"- {p}" for p in (files or [])) or "(none)"

        # Inline small text file contents with conservative limits
        inline_snippets: list[str] = []
        MAX_FILES = 5
        MAX_BYTES_PER_FILE = 20_000  # 20 KB per file
        total = 0
        for p in (files or [])[:MAX_FILES]:
            try:
                fp = Path(p)
                if not fp.exists() or not fp.is_file():  # skip missing
                    inline_snippets.append(f"--- {p} (missing) ---")
                    continue
                size = fp.stat().st_size
                if size > MAX_BYTES_PER_FILE:
                    inline_snippets.append(
                        f"--- {p} (skipped: {size} bytes > {MAX_BYTES_PER_FILE}) ---"
                    )
                    continue
                raw = fp.read_bytes()
                if b"\x00" in raw:  # naive binary check
                    inline_snippets.append(f"--- {p} (skipped: binary) ---")
                    continue
                text = raw.decode("utf-8", errors="replace")
                snippet = text[:MAX_BYTES_PER_FILE]
                total += len(snippet)
                inline_snippets.append(f"--- {p} ({len(snippet)} bytes) ---\n{snippet}".rstrip())
            except Exception as e:  # never break judging
                inline_snippets.append(f"--- {p} (error reading: {e}) ---")

        files_content_block = (
            "\n\nFile contents (truncated/limited):\n" + "\n\n".join(inline_snippets)
            if inline_snippets
            else ""
        )

        user_prompt = f"""
            User question:
            {question}

            Assistant answer (Markdown):
            {answer}

            Generated files (paths):
            {files_section}{files_content_block}

            Evaluation request (instructions for the judge):
            {judge_request}

            Task:
            1) Score each rubric criterion from 0-100.
            2) Compute the weighted overall score (0-100) according to the rubric weights.
            3) Identify concrete issues (if any).
            4) Provide 2-6 actionable suggestions.

            Return ONLY a valid object for the `Judgment` schema.
        """.strip()

        result, nodes = await run_agent(agent, user_prompt)
        # Attach the originating prompt so it can be persisted as an artifact.
        try:
            result.judge_prompt = user_prompt  # attribute defined in Judgment schema
        except Exception:  # pragma: no cover - defensive
            pass
        return result

    # ── helpers ──────────────────────────────────────────────────────────────

    def _system_prompt(self, rubric: list[RubricCriterion], extra: str) -> str:
        rubric_md = rubric_to_markdown(rubric)
        return f"""
            You are an impartial evaluator (LLM-as-a-Judge). Return ONLY JSON matching the `Judgment` schema:

            {{
            "score": 0-100,
            "pass_fail": true/false,
            "reasoning": "...",
            "criteria_scores": {{ "<criterion>": 0-100, ... }},
            "issues": ["..."],
            "suggestions": ["..."]
            }}

            Rubric:
            {rubric_md}
            {rubric_weight_note(rubric)}

            Rules:
            - Be strict but fair; penalize hallucinations and vague/irreproducible methods.
            - If safety/compliance concerns exist, cap the overall score at 60.
            - Keep suggestions concrete and actionable.
            {extra}
        """.strip()
