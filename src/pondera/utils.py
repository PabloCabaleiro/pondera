import re
from pathlib import Path

import yaml

from pondera.models.case import CaseSpec
from pondera.errors import ValidationError
from pondera.models.rubric import RubricCriterion


def apply_prejudge_checks(answer_md: str, case: CaseSpec) -> list[str]:
    """Run simple textual assertions against the answer.

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


def choose_rubric(
    case_rubric: list[RubricCriterion] | None, default_rubric: list[RubricCriterion] | None
) -> list[RubricCriterion] | None:
    """Return per-case rubric override or fall back to provided default."""
    return case_rubric or default_rubric


def compute_pass(
    *,
    precheck_failures: list[str],
    overall_threshold: int,
    per_criterion_thresholds: dict[str, int],
    criteria_scores: dict[str, int],
    overall_score: int,
) -> bool:
    """Decide overall pass/fail combining pre-checks, overall and per-criterion thresholds."""
    if precheck_failures:
        return False
    if overall_score < overall_threshold:
        return False
    for k, th in (per_criterion_thresholds or {}).items():
        if criteria_scores.get(k, 0) < th:
            return False
    return True


def default_rubric() -> list[RubricCriterion]:
    """Built-in rubric used when none is supplied."""
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


def load_case_yaml(path: str | Path) -> CaseSpec:
    """Load a YAML case file into a CaseSpec, raising ValidationError on schema issues."""
    p = Path(path)
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    try:
        return CaseSpec.model_validate(data)
    except Exception as ex:  # pydantic.ValidationError or other
        raise ValidationError(f"Invalid CaseSpec YAML '{path}': {ex}") from ex


def rubric_to_markdown(rubric: list[RubricCriterion]) -> str:
    """Render rubric as concise markdown bullet list with weights."""
    return "\n".join(f"- **{c.name}** (w={c.weight:g}): {c.description}" for c in rubric)


def rubric_weight_note(rubric: list[RubricCriterion]) -> str:
    """Short weight normalization note for inclusion in prompts."""
    tw = sum(c.weight for c in rubric)
    return f"(If weights do not sum to 1, normalize by total weight {tw:g}.)"
