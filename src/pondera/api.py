# src/pondera/api.py

import asyncio
import time
from pathlib import Path


from pondera.judge.base import Judge
from pondera.runner.base import Runner, ProgressCallback, normalize_run_result, emit_progress
from pondera.models.evaluation import EvaluationResult
from pondera.models.rubric import RubricCriterion
from pondera.settings import get_settings
from pondera.utils import load_case_yaml, apply_prejudge_checks, compute_pass, choose_rubric


async def evaluate_case_async(
    case_yaml_path: str | Path,
    *,
    runner: Runner,
    judge: Judge,
    default_rubric: list[RubricCriterion] | None = None,
    progress: ProgressCallback | None = None,
) -> EvaluationResult:
    """
    Async core: load a YAML case, run the user-provided runner, judge the answer,
    apply thresholds and pre-judge checks, and return an EvaluationResult.

    - `runner`: your implementation of the Runner protocol
    - `judge`:  your implementation of the Judge protocol
    - `default_rubric`: optional project-level rubric (used if the case doesn't set one)
    - `progress`: optional async callback to receive progress lines from the runner
    """
    get_settings()
    case = load_case_yaml(case_yaml_path)

    # 1) Run the case through the runner
    await emit_progress(progress, f"pondera: running case '{case.id}'…")
    t0 = time.perf_counter()
    raw_run = await runner.run(
        question=case.input.query,
        attachments=case.input.attachments,
        params=case.input.params,
        progress=progress,
    )
    run_res = normalize_run_result(raw_run, question=case.input.query)
    t1 = time.perf_counter()

    # 2) Pre-judge checks (strings/regex)
    failures = apply_prejudge_checks(run_res.answer_markdown or "", case)

    # 3) Judge the answer
    use_rubric = choose_rubric(case.judge.rubric, default_rubric)
    await emit_progress(progress, "pondera: judging answer…")
    t2 = time.perf_counter()
    judgment = await judge.judge(
        question=case.input.query,
        answer_markdown=run_res.answer_markdown or "",
        judge_request=case.judge.request,
        rubric=use_rubric,  # judge will fall back to its own default if None
        model=case.judge.model,  # optional per-case model override
        system_append=case.judge.system_append,
    )
    t3 = time.perf_counter()

    # 4) Compute final pass/fail using thresholds from the case
    overall_th = case.judge.overall_threshold
    percrit_th = case.judge.per_criterion_thresholds or {}
    passed = compute_pass(
        precheck_failures=failures,
        overall_threshold=overall_th,
        per_criterion_thresholds=percrit_th,
        criteria_scores=judgment.criteria_scores,
        overall_score=judgment.score,
    )

    # 5) Package result
    timings = {
        "runner_s": t1 - t0,
        "judge_s": t3 - t2,
        "total_s": (t3 - t0),
    }

    return EvaluationResult(
        case_id=case.id,
        case=case,
        run=run_res,
        judgment=judgment,
        precheck_failures=failures,
        overall_threshold=overall_th,
        per_criterion_thresholds=percrit_th,
        passed=passed,
        timings_s=timings,
    )


def evaluate_case(
    case_yaml_path: str | Path,
    *,
    runner: Runner,
    judge: Judge,
    default_rubric: list[RubricCriterion] | None = None,
    progress: ProgressCallback | None = None,
) -> EvaluationResult:
    """
    Sync wrapper around `evaluate_case_async`.

    Note:
    - If an event loop is already running (e.g., Jupyter), call the async version instead.
    """
    # If an asyncio event loop is already running (e.g., in Jupyter), it raises a RuntimeError and suggests using the async version instead.
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        raise RuntimeError(
            "An asyncio event loop is running. "
            "Use `await evaluate_case_async(...)` in async contexts."
        )

    return asyncio.run(
        evaluate_case_async(
            case_yaml_path,
            runner=runner,
            judge=judge,
            default_rubric=default_rubric,
            progress=progress,
        )
    )
