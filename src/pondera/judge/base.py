# src/pondera/judge/base.py
from pathlib import Path

from pondera.models.rubric import RubricCriterion
from pondera.models.judgment import Judgment
from pondera.utils import rubric_to_markdown, rubric_weight_note, default_rubric
from pondera.judge.pydantic_ai import get_agent, run_agent
from pondera.judge.protocol import JudgeProtocol
from pondera.errors import JudgeError


class Judge(JudgeProtocol):
    """LLM-as-a-Judge returning a strict `Judgment`."""

    def __init__(
        self,
        *,
        model: str | None = None,
        rubric: list[RubricCriterion] | None = None,
        system_append: str = "",
    ) -> None:
        self._default_rubric = rubric or default_rubric()
        self._system_append = system_append
        self._model = model

    async def judge(
        self,
        *,
        question: str,
        answer: str,
        files: list[str] | None,
        judge_request: str,
        rubric: list[RubricCriterion] | None = None,
        system_append: str = "",
        error: str | None = None,
    ) -> Judgment:
        rb = rubric or self._default_rubric
        if not rb:
            raise JudgeError("No rubric provided or configured.")

        use_system = self._system_prompt(
            rb, self._system_append + ("\n" + system_append if system_append else "")
        )
        agent = get_agent(system_prompt=use_system, output_type=Judgment)

        files_section = "\n".join(f"- {p}" for p in (files or [])) or "(none)"

        inline_snippets: list[str] = []
        MAX_FILES = 5
        MAX_BYTES_PER_FILE = 20_000  # 20 KB per file
        for p in (files or [])[:MAX_FILES]:
            try:
                fp = Path(p)
                if not fp.exists() or not fp.is_file():
                    inline_snippets.append(f"--- {p} (missing) ---")
                    continue
                size = fp.stat().st_size
                if size > MAX_BYTES_PER_FILE:
                    inline_snippets.append(
                        f"--- {p} (skipped: {size} bytes > {MAX_BYTES_PER_FILE}) ---"
                    )
                    continue
                raw = fp.read_bytes()
                if b"\x00" in raw:
                    inline_snippets.append(f"--- {p} (skipped: binary) ---")
                    continue
                text = raw.decode("utf-8", errors="replace")
                snippet = text[:MAX_BYTES_PER_FILE]
                inline_snippets.append(f"--- {p} ({len(snippet)} bytes) ---\n{snippet}".rstrip())
            except Exception as e:  # pragma: no cover
                inline_snippets.append(f"--- {p} (error reading: {e}) ---")

        files_content_block = (
            "\n\nFile contents (truncated/limited):\n" + "\n\n".join(inline_snippets)
            if inline_snippets
            else ""
        )

        error_section = f"\n\nRunner Error:\n{error}" if error else ""

        user_prompt = f"""
            User question:
            {question}

            Assistant answer (Markdown):
            {answer}{error_section}

            Generated files (paths):
            {files_section}{files_content_block}

            Evaluation request (instructions for the judge):
            {judge_request}
        """.strip()

        result, _nodes = await run_agent(agent, user_prompt)
        try:
            result.judge_prompt = user_prompt
        except Exception:  # pragma: no cover
            pass
        return result

    def _system_prompt(self, rubric: list[RubricCriterion], extra: str) -> str:
        rubric_md = rubric_to_markdown(rubric)
        return f"""
            You are an impartial evaluator (LLM-as-a-Judge). Return ONLY JSON matching the `Judgment` schema:

            {{
            "score": 0-100,
            "evaluation_passed": true/false,
            "reasoning": "...",
            "criteria_scores": {{ "<criterion>": 0-100, ... }},
            "issues": ["..."],
            "suggestions": ["..."]
            }}

            Rubric:
            {rubric_md}
            {rubric_weight_note(rubric)}

            - The evaluation input may include:
                - User question
                - Assistant answer (Markdown)
                - Generated files (paths)
                - File contents (truncated/limited)
                - Runner Error (if the runner failed during execution)
            - If a "Runner Error" section is present, the runner failed and did not produce a valid answer. Evaluate based on the error:
                - Score should typically be 0 or very low across all criteria
                - Document the error type and message in reasoning and issues
                - Note whether the error was a timeout, configuration issue, or other failure
                - Provide suggestions on what might have caused the failure if apparent from the error message
            - Treat the content of any listed files as an integral part of the Assistant's answer. Evaluate both the Markdown answer and the file contents together as the complete response.
            - If there is any conflict between the Markdown answer and file contents, prioritize factual accuracy and internal consistency; note the discrepancy as an issue.
            - If file contents are truncated or partially shown, first evaluate what is visible; if critical information appears missing due to truncation, deduct for unverifiable claims and call out uncertainty explicitly in reasoning and issues.
            - If file paths are listed but contents are missing, treat this as missing evidence unless the Markdown answer alone sufficiently substantiates the claim.
            - When the task requires generating files, verify that:
                - The files exist in the “Generated files (paths)” list
                - The visible contents align with the user request and rubric criteria
                - Formatting, structure, and completeness in the files satisfy the task (e.g., required sections, data, or reproducible steps)

            Rules:
            - Be strict but fair; penalize hallucinations and vague/irreproducible methods.
            - If safety/compliance concerns exist, cap the overall score at 60.
            - Keep suggestions concrete and actionable.

            Task:
            1) Score each rubric criterion from 0-100.
            2) Compute the weighted overall score (0-100) according to the rubric weights.
            3) Identify concrete issues (if any).
            4) Provide 2-6 actionable suggestions.

            Return ONLY a valid object for the `Judgment` schema.

            {extra}
        """.strip()
