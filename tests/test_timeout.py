import asyncio
from pathlib import Path
from typing import Any

import pytest

from pondera.api import evaluate_case_async
from pondera.models.run import RunResult
from pondera.judge.protocol import JudgeProtocol
from pondera.models.judgment import Judgment
from pondera.models.rubric import RubricCriterion

TEST_DATA_DIR = Path(__file__).parent / "data"
TIMEOUT_CASE_PATH = TEST_DATA_DIR / "timeout_case.yaml"


class SleepRunner:
    async def run(
        self,
        *,
        question: str,
        attachments: list[str] | None = None,
        params: dict[str, Any] | None = None,
        progress: Any | None = None,
    ) -> RunResult:
        await asyncio.sleep(2)  # longer than timeout_s=1
        return RunResult(question=question, answer="late answer")


class FastRunner:
    async def run(
        self,
        *,
        question: str,
        attachments: list[str] | None = None,
        params: dict[str, Any] | None = None,
        progress: Any | None = None,
    ) -> RunResult:
        return RunResult(question=question, answer="fast answer")


class SlowJudge(JudgeProtocol):
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
        await asyncio.sleep(2)  # longer than timeout
        return Judgment(
            score=0,
            pass_fail=False,
            reasoning="timeout placeholder",
            criteria_scores={"overall": 0},
            issues=["Should have timed out"],
            suggestions=[],
        )


@pytest.mark.asyncio
async def test_runner_timeout() -> None:
    with pytest.raises(asyncio.TimeoutError):
        await evaluate_case_async(TIMEOUT_CASE_PATH, runner=SleepRunner())


@pytest.mark.asyncio
async def test_judge_timeout() -> None:
    # Runner is fast; judge will exceed timeout
    with pytest.raises(asyncio.TimeoutError):
        await evaluate_case_async(TIMEOUT_CASE_PATH, runner=FastRunner(), judge=SlowJudge())
