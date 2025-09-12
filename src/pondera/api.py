import asyncio
import time
from pathlib import Path
from typing import Any

from pondera.judge.protocol import JudgeProtocol
from pondera.judge import Judge
from pondera.runner.base import Runner, ProgressCallback, emit_progress
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
from pondera.io.artifacts import write_case_artifacts
from pondera.io.artifacts import write_multi_evaluation_artifacts  # type: ignore


async def _execute_case_once(
    *,
    case: "CaseSpec",
    runner: Runner,
    judge: JudgeProtocol | None,
    default_rubric: list[RubricCriterion] | None,
    progress: ProgressCallback | None,
) -> EvaluationResult:
    """Internal single execution helper (no YAML reload)."""
    await emit_progress(progress, f"pondera: running case '{case.id}'…")
    t0 = time.perf_counter()
    run_res = await _run_case(case, runner, progress)
    t1 = time.perf_counter()
    failures = apply_prejudge_checks(run_res.answer or "", case)
    use_rubric = choose_rubric(case.judge.rubric, default_rubric)
    await emit_progress(progress, "pondera: judging answer…")
    t2 = time.perf_counter()
    the_judge: JudgeProtocol = judge or Judge()
    judgment = await _judge_case(case, run_res, the_judge, use_rubric)
    t3 = time.perf_counter()
    timings = _get_timings(t0, t1, t2, t3)
    passed = _compute_pass(case, failures, judgment)
    return EvaluationResult(
        case_id=case.id,
        case=case,
        run=run_res,
        judgment=judgment,
        precheck_failures=failures,
        overall_threshold=case.judge.overall_threshold,
        per_criterion_thresholds=case.judge.per_criterion_thresholds or {},
        passed=passed,
        timings_s=timings,
    )


async def evaluate_case_async(
    case_yaml_path: str | Path,
    *,
    runner: Runner,
    judge: JudgeProtocol | None = None,
    default_rubric: list[RubricCriterion] | None = None,
    progress: ProgressCallback | None = None,
    primary_metric: AggregationMetric = AggregationMetric.mean,
    artifacts_root: Path | str | None = None,
) -> MultiEvaluationResult:
    """Evaluate a case (any repetitions) and always return a MultiEvaluationResult.

    Rationale: a single uniform return type simplifies downstream handling.
    For `repetitions == 1`, the result contains exactly one EvaluationResult in
    `evaluations` and the aggregates are computed over that single sample.
    """
    settings_obj = get_settings()
    if artifacts_root is None:
        artifacts_root = settings_obj.artifacts_dir
    case = load_case_yaml(case_yaml_path)
    reps = max(1, getattr(case, "repetitions", 1))
    if reps == 1:
        # Run exactly once, then wrap in MultiEvaluationResult for a stable API.
        evaluations = [
            await _execute_case_once(
                case=case,
                runner=runner,
                judge=judge,
                default_rubric=default_rubric,
                progress=progress,
            )
        ]
    else:
        evaluations = await _run_multiple_evaluations(
            case, reps, runner, judge, default_rubric, progress
        )
    aggregates, passed_primary = _aggregate_multi_evaluations(evaluations, primary_metric)
    multi = MultiEvaluationResult(
        case_id=case.id,
        evaluations=evaluations,
        aggregates=aggregates,
        passed=passed_primary,
        primary_metric=primary_metric,
    )
    if artifacts_root:
        # Preserve existing single-run artifact layout for backward compatibility.
        if reps == 1:
            write_case_artifacts(artifacts_root, evaluations[0])
        else:
            write_multi_evaluation_artifacts(artifacts_root, multi)
    return multi


async def _run_case(case: "CaseSpec", runner: Runner, progress: ProgressCallback | None) -> Any:
    """Run the case using the runner enforcing per-case timeout."""
    try:
        return await asyncio.wait_for(
            runner.run(
                question=case.input.query,
                attachments=case.input.attachments,
                params=case.input.params,
                progress=progress,
            ),
            timeout=case.timeout_s,
        )
    except asyncio.TimeoutError as ex:  # pragma: no cover - message path
        raise asyncio.TimeoutError(
            f"runner timed out after {case.timeout_s}s for case '{case.id}'"
        ) from ex


async def _judge_case(
    case: "CaseSpec", run_res: Any, judge: JudgeProtocol, rubric: list[RubricCriterion] | None
) -> Any:
    """Judge the answer enforcing per-case timeout."""
    try:
        return await asyncio.wait_for(
            judge.judge(
                question=case.input.query,
                answer=run_res.answer or "",
                files=run_res.files,
                judge_request=case.judge.request,
                rubric=rubric,
                system_append=case.judge.system_append,
            ),
            timeout=case.timeout_s,
        )
    except asyncio.TimeoutError as ex:  # pragma: no cover - message path
        raise asyncio.TimeoutError(
            f"judge timed out after {case.timeout_s}s for case '{case.id}'"
        ) from ex


def _get_timings(t0: float, t1: float, t2: float, t3: float) -> dict[str, float]:
    """Return timing measurements."""
    return {"runner_s": t1 - t0, "judge_s": t3 - t2, "total_s": (t3 - t0)}


def _compute_pass(case: "CaseSpec", failures: list[str], judgment: Any) -> bool:
    """Compute pass/fail for the evaluation."""
    return compute_pass(
        precheck_failures=failures,
        overall_threshold=case.judge.overall_threshold,
        per_criterion_thresholds=case.judge.per_criterion_thresholds or {},
        criteria_scores=judgment.criteria_scores,
        overall_score=judgment.score,
    )


async def _run_multiple_evaluations(
    case: "CaseSpec",
    reps: int,
    runner: Runner,
    judge: JudgeProtocol | None,
    default_rubric: list[RubricCriterion] | None,
    progress: ProgressCallback | None,
) -> list[EvaluationResult]:
    """Run multiple evaluations for repetitions."""
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
    return evaluations


def _aggregate_multi_evaluations(
    evaluations: list[EvaluationResult],
    primary_metric: AggregationMetric,
) -> tuple[CriteriaAggregates, bool]:
    """Aggregate results and compute pass/fail for multi-evaluations."""
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
    # Reuse unified compute_pass logic by synthesizing an aggregated score dict.
    aggregated_criteria_scores: dict[str, int] = {}
    for k, agg in per_crit_aggs.items():
        aggregated_criteria_scores[k] = int(getattr(agg, primary_metric.value))
    overall_value_for_pass = getattr(overall_agg, primary_metric.value)
    # Aggregate any pre-check failures across runs (if any run failed a pre-check we fail overall).
    aggregated_precheck_failures: list[str] = []
    for idx, ev in enumerate(evaluations):
        if ev.precheck_failures:
            # Prefix with run index for traceability.
            aggregated_precheck_failures.extend([f"run {idx+1}: {m}" for m in ev.precheck_failures])
    passed_primary = compute_pass(
        precheck_failures=aggregated_precheck_failures,
        overall_threshold=evaluations[0].overall_threshold,
        per_criterion_thresholds=evaluations[0].per_criterion_thresholds or {},
        criteria_scores=aggregated_criteria_scores,
        overall_score=int(overall_value_for_pass),
    )
    return aggregates, passed_primary


def evaluate_case(
    case_yaml_path: str | Path,
    *,
    runner: Runner,
    judge: JudgeProtocol | None = None,
    default_rubric: list[RubricCriterion] | None = None,
    progress: ProgressCallback | None = None,
    primary_metric: AggregationMetric = AggregationMetric.mean,
    artifacts_root: Path | str | None = None,
) -> MultiEvaluationResult:
    """Synchronous wrapper returning a MultiEvaluationResult (see async docstring)."""
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
            artifacts_root=artifacts_root,
        )
    )
