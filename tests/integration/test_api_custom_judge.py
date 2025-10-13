"""Integration tests for the pondera API."""

from __future__ import annotations

import pytest
from pathlib import Path
from typing import Any

from pondera.api import evaluate_case
from pondera.models.multi_evaluation import MultiEvaluationResult
from pondera.models.run import RunResult
from pondera.models.judgment import Judgment
from pondera.runner.base import ProgressCallback
from pondera.judge.base import JudgeProtocol


class DummyRunner:
    async def run(
        self,
        *,
        question: str,
        attachments: list[str] | None = None,
        params: dict[str, Any] | None = None,
        progress: ProgressCallback | None = None,
    ) -> RunResult:
        return RunResult(
            question=question,
            answer="Paris is the capital of France",
            files=["tests/integration/data/output_file.txt"],
            metadata={"test": True, "params": params or {}},
        )


class AlwaysCorrectJudge(JudgeProtocol):
    async def judge(
        self,
        *,
        question: str,
        answer: str,
        files: list[str] | None,
        judge_request: str,
        rubric: list[Any] | None = None,
        system_append: str = "",
        error: str | None = None,
    ) -> Judgment:
        return Judgment(
            score=100,
            evaluation_passed=True,
            reasoning="Always correct",
            criteria_scores={"overall": 100},
            issues=[],
            suggestions=[],
            judge_prompt=f"Always correct judge prompt {question} {files} {answer} {judge_request} {rubric} {system_append}",
        )


@pytest.mark.integration
class TestCustomJudgeAPIIntegration:
    """Integration tests for the pondera API functions."""

    def test_evaluate_case_sync_basic(self) -> None:
        """Test synchronous evaluation of a basic case."""
        case_path = Path(__file__).parent / "data" / "basic_integration.yaml"
        runner = DummyRunner()
        judge = AlwaysCorrectJudge()

        result = evaluate_case(case_yaml_path=case_path, runner=runner, judge=judge)
        assert isinstance(result, MultiEvaluationResult)
        assert result.passed
        assert len(result.evaluations) == 1
        ev = result.evaluations[0]
        assert ev.case_id == "integration_basic_test"
        assert result.passed
        assert ev.run.question == "What is the capital of France?"
        assert ev.run.answer == "Paris is the capital of France"
        assert ev.judgment is not None
        assert ev.judgment.score == 100
        assert ev.judgment.judge_prompt.startswith("Always correct judge prompt")
        assert "tests/integration/data/output_file.txt" in ev.judgment.judge_prompt
