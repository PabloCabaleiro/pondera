# src/pondera/api.py

import asyncio
import time
from pathlib import Path
from typing import Union, Any

from pondera.judge.base import Judge
from pondera.runner.base import Runner, ProgressCallback, normalize_run_result, emit_progress
from pondera.models.evaluation import EvaluationResult
from pondera.models.rubric import RubricCriterion
from pondera.models.multi_evaluation import (
    MultiEvaluationResult,
    AggregationMetric,
    aggregate_numbers,
    CriteriaAggregates,
)
from pondera.models.case import CaseSpec
from pondera.settings import get_settings
from pondera.utils import load_case_yaml, apply_prejudge_checks, compute_pass, choose_rubric


async def _execute_case_once(
    *,
    case: "CaseSpec",
    runner: Runner,
    judge: Judge,
    default_rubric: list[RubricCriterion] | None,
    progress: ProgressCallback | None,
) -> EvaluationResult:
    """Internal single execution helper (no YAML reload)."""
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
    failures = apply_prejudge_checks(run_res.answer_markdown or "", case)
    use_rubric = choose_rubric(case.judge.rubric, default_rubric)
    await emit_progress(progress, "pondera: judging answer…")
    t2 = time.perf_counter()
    judgment = await judge.judge(
        question=case.input.query,
        answer_markdown=run_res.answer_markdown or "",
        judge_request=case.judge.request,
        rubric=use_rubric,
        system_append=case.judge.system_append,
    )
    t3 = time.perf_counter()
    overall_th = case.judge.overall_threshold
    percrit_th = case.judge.per_criterion_thresholds or {}
    passed = compute_pass(
        precheck_failures=failures,
        overall_threshold=overall_th,
        per_criterion_thresholds=percrit_th,
        criteria_scores=judgment.criteria_scores,
        overall_score=judgment.score,
    )
    timings = {"runner_s": t1 - t0, "judge_s": t3 - t2, "total_s": (t3 - t0)}
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


async def evaluate_case_async(
    case_yaml_path: str | Path,
    *,
    runner: Runner,
    judge: Judge,
    default_rubric: list[RubricCriterion] | None = None,
    progress: ProgressCallback | None = None,
    primary_metric: AggregationMetric = AggregationMetric.mean,
) -> Union[EvaluationResult, MultiEvaluationResult]:
    """Evaluate a case (optionally multiple repetitions) and return results.

    - Reads `repetitions` from the case YAML. If `repetitions == 1` returns a single `EvaluationResult`.
    - If `repetitions > 1`, executes the case multiple times and returns a `MultiEvaluationResult` with
      aggregated stats (min/max/mean/median/stdev/variance) for overall score and per-criterion scores.
    - `primary_metric` controls which aggregate is used to decide pass/fail of the aggregated result.
    """
    get_settings()
    case = load_case_yaml(case_yaml_path)
    reps = max(1, getattr(case, "repetitions", 1))
    if reps == 1:
        return await _execute_case_once(
            case=case,
            runner=runner,
            judge=judge,
            default_rubric=default_rubric,
            progress=progress,
        )

    evaluations: list[EvaluationResult] = []
    for i in range(reps):
        if progress:
            await progress(f"pondera: repetition {i+1}/{reps} for case '{case.id}'")
        ev = await _execute_case_once(
            case=case,
            runner=runner,
            judge=judge,
            default_rubric=default_rubric,
            progress=progress,
        )
        evaluations.append(ev)

    # Aggregation logic (same as previous multi API)
    overall_scores = [ev.judgment.score for ev in evaluations]
    overall_agg = aggregate_numbers([float(s) for s in overall_scores], primary_metric)
    criteria_keys: set[str] = set()
    for ev in evaluations:
        criteria_keys.update(ev.judgment.criteria_scores.keys())
    per_crit_aggs: dict[str, Any] = {}
    for key in sorted(criteria_keys):
        vals = [float(ev.judgment.criteria_scores.get(key, 0)) for ev in evaluations]
        per_crit_aggs[key] = aggregate_numbers(vals, primary_metric)
    aggregates = CriteriaAggregates(overall=overall_agg, per_criterion=per_crit_aggs)
    overall_value_for_pass = getattr(overall_agg, primary_metric.value)
    case_overall_th = evaluations[0].overall_threshold
    percrit_th = evaluations[0].per_criterion_thresholds
    criteria_ok = True
    for k, th in (percrit_th or {}).items():
        crit_val = getattr(per_crit_aggs[k], primary_metric.value) if k in per_crit_aggs else 0.0
        if crit_val < th:
            criteria_ok = False
            break
    passed_primary = (overall_value_for_pass >= case_overall_th) and criteria_ok
    return MultiEvaluationResult(
        case_id=case.id,
        evaluations=evaluations,
        aggregates=aggregates,
        passed_primary=passed_primary,
        primary_metric=primary_metric,
    )


def evaluate_case(
    case_yaml_path: str | Path,
    *,
    runner: Runner,
    judge: Judge,
    default_rubric: list[RubricCriterion] | None = None,
    progress: ProgressCallback | None = None,
    primary_metric: AggregationMetric = AggregationMetric.mean,
) -> Union[EvaluationResult, MultiEvaluationResult]:
    """Sync wrapper around `evaluate_case_async` supporting repetitions (see async docstring)."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop and loop.is_running():
        raise RuntimeError(
            "An asyncio event loop is running. Use `await evaluate_case_async(...)` in async contexts."
        )
    return asyncio.run(
        evaluate_case_async(
            case_yaml_path,
            runner=runner,
            judge=judge,
            default_rubric=default_rubric,
            progress=progress,
            primary_metric=primary_metric,
        )
    )
