# src/pondera/utils.py

import re
from pathlib import Path

import yaml

from pondera.models.case import CaseSpec
from pondera.models.rubric import RubricCriterion


def load_case_yaml(path: str | Path) -> CaseSpec:
    p = Path(path)
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    return CaseSpec.model_validate(data)


def apply_prejudge_checks(answer_md: str, case: CaseSpec) -> list[str]:
    """
    Returns a list of failure messages; empty list means all checks passed.
    """
    failures: list[str] = []
    exp = case.expect

    low = answer_md.lower()

    for s in exp.must_contain:
        if s.lower() not in low:
            failures.append(f"must_contain failed: {s!r}")

    for s in exp.must_not_contain:
        if s.lower() in low:
            failures.append(f"must_not_contain failed: {s!r}")

    for pattern in exp.regex_must_match:
        if not re.search(pattern, answer_md, flags=re.I | re.M):
            failures.append(f"regex_must_match failed: {pattern!r}")

    return failures


def compute_pass(
    *,
    precheck_failures: list[str],
    overall_threshold: int,
    per_criterion_thresholds: dict[str, int],
    criteria_scores: dict[str, int],
    overall_score: int,
) -> bool:
    if precheck_failures:
        return False
    if overall_score < overall_threshold:
        return False
    for k, th in (per_criterion_thresholds or {}).items():
        if criteria_scores.get(k, 0) < th:
            return False
    return True


def choose_rubric(
    case_rubric: list[RubricCriterion] | None, default_rubric: list[RubricCriterion] | None
) -> list[RubricCriterion] | None:
    # Prefer case override; else project/default; else None (judge will have its own default)
    return case_rubric or default_rubric


def rubric_to_markdown(rubric: list[RubricCriterion]) -> str:
    """
    Render a rubric into concise markdown bullet points with weights.
    """
    return "\n".join(f"- **{c.name}** (w={c.weight:g}): {c.description}" for c in rubric)


def default_rubric() -> list[RubricCriterion]:
    """
    Default rubric used when none is provided.
    Kept "private" by convention but importable by implementations.
    """
    return [
        RubricCriterion(
            name="correctness",
            weight=0.40,
            description="Facts and computations are accurate; no hallucinations.",
        ),
        RubricCriterion(
            name="completeness",
            weight=0.25,
            description="Addresses the question fully with sufficient depth.",
        ),
        RubricCriterion(
            name="methodology_repro",
            weight=0.15,
            description="Steps/parameters clear enough to reproduce.",
        ),
        RubricCriterion(
            name="safety_compliance",
            weight=0.10,
            description="No unsafe/PHI/proprietary content.",
        ),
        RubricCriterion(
            name="presentation",
            weight=0.10,
            description="Clear structure and formatting.",
        ),
    ]


def rubric_weight_note(rubric: list[RubricCriterion]) -> str:
    """
    Brief instruction for how to handle non-normalized weights.
    """
    tw = sum(c.weight for c in rubric)
    return f"(If weights do not sum to 1, normalize by total weight {tw:g}.)"
