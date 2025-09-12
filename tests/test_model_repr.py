from pondera.models.run import RunResult
from pondera.models.judgment import Judgment
from pondera.models.evaluation import EvaluationResult
from pondera.models.case import CaseSpec, CaseInput, CaseExpectations, CaseJudge


def _case() -> CaseSpec:
    return CaseSpec(
        id="demo",
        input=CaseInput(query="Q"),
        expect=CaseExpectations(),
        judge=CaseJudge(),
        timeout_s=5,
        repetitions=1,
    )


def test_runresult_str_repr() -> None:
    r = RunResult(question="Q", answer="A", artifacts=["a.txt"], files=["a.txt"], metadata={"k": 1})
    s = str(r)
    rp = repr(r)
    assert "RunResult" in s and "artifacts=1" in s
    assert "RunResult(" in rp and "answer_len" in rp


def test_judgment_str_repr() -> None:
    j = Judgment(
        score=90,
        evaluation_passed=True,
        reasoning="All good",
        criteria_scores={"correctness": 90},
    )
    s = str(j)
    rp = repr(j)
    assert "Judgment(score=90" in s
    assert "criteria_scores={'correctness': 90}" in rp


def test_evaluation_result_str_repr() -> None:
    r = RunResult(question="Q", answer="A")
    j = Judgment(
        score=80, evaluation_passed=True, reasoning="Fine", criteria_scores={"correctness": 80}
    )
    ev = EvaluationResult(
        case_id="demo",
        case=_case(),
        run=r,
        judgment=j,
        precheck_failures=[],
        overall_threshold=60,
        per_criterion_thresholds={},
        passed=True,
        timings_s={},
    )
    s = str(ev)
    rp = repr(ev)
    assert "EvaluationResult(case_id=demo" in s
    assert "score=80" in rp
