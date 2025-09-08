# src/pondera/cli.py

import asyncio
import importlib
import inspect

from pathlib import Path
from typing import Iterable

import typer

from pondera.api import evaluate_case_async
from pondera.io.artifacts import write_case_artifacts
from pondera.judge.pydantic_ai import PydanticAIJudge
from pondera.runner.base import Runner
from pondera.settings import get_settings

app = typer.Typer(help="Pondera — YAML-first, pluggable evaluation runner.")


def _iter_case_files(cases_dir: Path) -> Iterable[Path]:
    for suffix in (".yaml", ".yml"):
        yield from sorted(cases_dir.rglob(f"*{suffix}"))


def _load_runner(target: str) -> Runner:
    """
    Accepts:
      --runner module:obj
    Where `obj` can be:
      - a factory function returning a Runner instance
      - a class with an async `run(...)` method (no-arg ctor)
      - an already-instantiated object exported at module level
    """
    if ":" not in target:
        raise typer.BadParameter("Expected format 'module:object', e.g. 'myproj.eval:make_runner'")

    mod_name, obj_name = target.split(":", 1)
    try:
        mod = importlib.import_module(mod_name)
    except Exception as e:
        raise typer.BadParameter(f"Cannot import module '{mod_name}': {e}") from e

    try:
        obj = getattr(mod, obj_name)
    except AttributeError as e:
        raise typer.BadParameter(f"Module '{mod_name}' has no attribute '{obj_name}'") from e

    # If it's a callable factory, call it
    if callable(obj) and not inspect.isclass(obj):
        inst = obj()
        if hasattr(inst, "run"):
            return inst  # type: ignore[return-value]
        raise typer.BadParameter(
            f"Factory '{target}' did not return an object with a 'run' method."
        )

    # If it's a class, instantiate with no args
    if inspect.isclass(obj):
        inst = obj()
        if hasattr(inst, "run"):
            return inst  # type: ignore[return-value]
        raise typer.BadParameter(f"Class '{target}' does not define a 'run' method.")

    # If it's an object with run, accept it
    if hasattr(obj, "run"):
        return obj  # type: ignore[return-value]

    raise typer.BadParameter(f"Object '{target}' is not a runner (missing 'run' method).")


@app.command("run")
def run_cases(
    cases_dir: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
        resolve_path=True,
        help="Directory with YAML cases.",
    ),
    runner: str = typer.Option(
        ...,
        "--runner",
        "-r",
        help="Runner import path 'module:object' (factory, class, or instance).",
    ),
    artifacts: Path = typer.Option(
        None, "--artifacts", "-a", help="Artifacts output directory (default from settings)."
    ),
    judge_model: str | None = typer.Option(
        None, "--judge-model", help="Override default judge model id."
    ),
    fail_fast: bool = typer.Option(False, "--fail-fast", help="Stop on first failure."),
) -> None:
    """
    Run all YAML cases found under <cases_dir> using the provided runner and the built-in PydanticAI judge.
    """
    settings = get_settings()
    out_dir = artifacts or Path(settings.artifacts_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Resolve runner and judge
    runner_inst: Runner = _load_runner(runner)
    judge = PydanticAIJudge(model=judge_model or None)

    # tiny async progress printer
    async def _progress(line: str) -> None:
        typer.echo(line)

    # Collect cases
    files = list(_iter_case_files(cases_dir))
    if not files:
        typer.echo(f"No YAML cases found in {cases_dir}", err=True)
        raise typer.Exit(code=2)

    total = len(files)
    passed = 0
    failed = 0

    async def _run_one(path: Path) -> None:
        nonlocal passed, failed
        res = await evaluate_case_async(
            path,
            runner=runner_inst,
            judge=judge,
            default_rubric=None,
            progress=_progress,
        )
        write_case_artifacts(out_dir, res)
        status = "PASS ✅" if res.passed else "FAIL ❌"
        typer.echo(
            f"[{res.case_id}] {status}  overall={res.judgment.score}  "
            f"(runner={res.timings_s.get('runner_s', 0):.2f}s, judge={res.timings_s.get('judge_s', 0):.2f}s)"
        )
        if res.passed:
            passed += 1
        else:
            failed += 1
            if fail_fast:
                raise typer.Exit(code=1)

    # Run sequentially (keeps output tidy for now)
    for p in files:
        try:
            typer.echo(f"\n=== Running case: {p.name} ===")
            asyncio.run(_run_one(p))
        except typer.Exit as ex:
            # propagate controlled exits (e.g., fail-fast)
            raise ex
        except Exception as e:
            typer.echo(f"Error while running {p}: {e}", err=True)
            failed += 1
            if fail_fast:
                raise typer.Exit(code=1)

    typer.echo(f"\nSummary: {passed}/{total} passed, {failed} failed")
    raise typer.Exit(code=0 if failed == 0 else 1)
