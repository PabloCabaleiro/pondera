# src/pondera/judge/base.py
from pondera.models.rubric import RubricCriterion
from pondera.models.judgment import Judgment
from pondera.settings import get_settings
from pondera.utils import rubric_to_markdown, rubric_weight_note, default_rubric
from pondera.judge.pydantic_ai import get_agent, run_agent


class JudgeError(RuntimeError):
    """Raised for judge configuration or runtime errors."""


class Judge:
    """
    LLM-as-a-judge built on get_agent and run_agent, returning a strict `Judgment`.

    - Model-agnostic: pass any backend id supported by your pydantic_ai setup.
    - Defaults are pulled from Pondera settings (PONDERA_JUDGE_MODEL, provider envs).
    - No MCP in MVP (can be added later).
    """

    def __init__(
        self,
        *,
        model: str | None = None,
        rubric: list[RubricCriterion] | None = None,
        system_append: str = "",
    ):
        settings = get_settings()
        self._default_model = model or settings.judge_model
        self._default_rubric = rubric or default_rubric()
        self._system_append = system_append

    async def judge(
        self,
        *,
        question: str,
        answer_markdown: str,
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

        user_prompt = f"""
            User question:
            {question}

            Assistant answer (Markdown):
            {answer_markdown}

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
