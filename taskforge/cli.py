"""Command line interface for TaskForge."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Annotated

import typer

from taskforge.actions import parse_action
from taskforge.env import TaskEnv
from taskforge.evaluate import read_report, report_table, run_episode, run_eval
from taskforge.filters import filter_tasks
from taskforge.loader import discover_tasks, load_task
from taskforge.models import TaskSpec, TaskValidationError
from taskforge.policies.base import Policy
from taskforge.policies.claude import ClaudePolicy
from taskforge.policies.random_policy import RandomPolicy
from taskforge.policies.scripted import ScriptedPolicy
from taskforge.reporting import discover_report_paths, generate_report_markdown
from taskforge.runners import DockerRunner, SubprocessRunner
from taskforge.sweep import (
    MEASURED_COST_PER_EPISODE_USD,
    estimate_sweep_cost,
    planned_sweep_episodes,
    run_sweep,
    sweep_report,
)
from taskforge.trajectory import read_trajectory, summarize_episode
from taskforge.verify import verify_task
from taskforge.viewer import write_viewer

app = typer.Typer(help="TaskForge task utilities.")
CONFIRM_EPISODE_THRESHOLD = 10


@app.command()
def validate(tasks_dir: Path) -> None:
    """Validate all tasks in a directory and print a result table."""
    task_files = sorted(tasks_dir.glob("*/task.yaml"))
    failures = 0
    typer.echo("TASK\tSTATUS\tDETAIL")
    for task_file in task_files:
        try:
            task = load_task(task_file)
        except TaskValidationError as exc:
            failures += 1
            typer.echo(f"{task_file.parent.name}\tFAIL\t{exc}")
        else:
            typer.echo(f"{task.id}\tOK\t{task.title}")
    if failures:
        raise typer.Exit(code=1)


@app.command()
def run(
    task_id: str,
    policy: str = typer.Option("scripted"),
    runner_name: str = typer.Option("subprocess", "--runner"),
    trajectory: Annotated[Path | None, typer.Option("--trajectory")] = None,
    verbose_trajectory: Annotated[bool, typer.Option("--verbose-trajectory")] = False,
    max_steps: Annotated[int | None, typer.Option("--max-steps")] = None,
    temperature: Annotated[float, typer.Option("--temperature")] = 0.0,
) -> None:
    """Run one task with a policy and print the episode result."""
    task = _find_task(task_id)
    seed = 0
    trajectory_path = trajectory or _default_run_trajectory(task_id=task.id, seed=seed)
    result = run_episode(
        task=task,
        policy=_policy_factory(policy, temperature=temperature)(seed),
        runner=_runner(runner_name),
        seed=seed,
        trajectory_path=trajectory_path,
        verbose_trajectory=verbose_trajectory,
        max_steps=max_steps,
    )
    typer.echo(result.model_dump_json(indent=2))


@app.command()
def inspect(task_id: str) -> None:
    """Print the parsed task specification."""
    task = _find_task(task_id)
    typer.echo(task.model_dump_json(indent=2))


@app.command()
def stats(trajectory_jsonl: Path) -> None:
    """Print aggregate stats for a trajectory."""
    summary = summarize_episode(read_trajectory(trajectory_jsonl))
    typer.echo(summary)


@app.command()
def replay(trajectory_jsonl: Path) -> None:
    """Replay recorded actions and assert the same terminal reward."""
    episode = read_trajectory(trajectory_jsonl)
    start = episode.records[0]
    task = _find_task(start.task_id)
    with TaskEnv(task) as env:
        env.reset()
        result = None
        for action_payload in episode.actions:
            result = env.step(parse_action(action_payload))
            if result.done:
                break
    if result is None:
        raise typer.BadParameter("trajectory contains no actions")
    if result.reward != episode.terminal_reward:
        raise typer.Exit(
            code=_echo_error(
                f"non-determinism detected: expected {episode.terminal_reward}, got {result.reward}"
            )
        )
    typer.echo(f"replay ok: terminal reward {result.reward}")


@app.command()
def eval(
    tasks_dir: Annotated[Path, typer.Option("--tasks")] = Path("tasks"),
    policy_name: Annotated[str, typer.Option("--policy")] = "scripted",
    n_samples: Annotated[int, typer.Option("--n")] = 3,
    max_workers: Annotated[int, typer.Option("--max-workers")] = 4,
    runner_name: Annotated[str, typer.Option("--runner")] = "subprocess",
    out_dir: Annotated[Path | None, typer.Option("--out")] = None,
    verbose_trajectory: Annotated[bool, typer.Option("--verbose-trajectory")] = False,
    max_steps: Annotated[int | None, typer.Option("--max-steps")] = None,
    temperature: Annotated[float, typer.Option("--temperature")] = 0.0,
    yes: Annotated[bool, typer.Option("--yes")] = False,
    max_cost_usd: Annotated[float | None, typer.Option("--max-cost-usd")] = None,
    tier: Annotated[int | None, typer.Option("--tier")] = None,
    tags: Annotated[list[str] | None, typer.Option("--tag")] = None,
) -> None:
    """Run a parallel policy evaluation and save report.json."""
    tasks = filter_tasks(discover_tasks(tasks_dir), tier=tier, tags=tags)
    episodes = len(tasks) * n_samples
    low_cost, high_cost = _estimated_cost_range(policy_name, episodes)
    typer.echo(
        f"Planned episodes: {episodes}; estimated cost range: "
        f"${low_cost:.4f}-${high_cost:.4f}"
    )
    if episodes > CONFIRM_EPISODE_THRESHOLD and not yes:
        raise typer.BadParameter("episode count exceeds threshold; pass --yes to proceed")
    output = out_dir or Path("runs") / f"eval-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    report = run_eval(
        tasks=tasks,
        policy_factory=_policy_factory(policy_name, temperature=temperature),
        n_samples=n_samples,
        max_workers=max_workers,
        runner_factory=lambda: _runner(runner_name),
        out_dir=output,
        max_cost_usd=max_cost_usd,
        verbose_trajectory=verbose_trajectory,
        max_steps=max_steps,
    )
    typer.echo(report_table(report))


@app.command()
def sweep(
    tasks_dir: Annotated[Path, typer.Option("--tasks")] = Path("tasks"),
    policy_name: Annotated[str, typer.Option("--policy")] = "claude",
    max_steps_csv: Annotated[str, typer.Option("--max-steps")] = "3,5,25",
    n_samples: Annotated[
        int,
        typer.Option(
            "--n",
            help=(
                "Samples per task/budget. Defaults to 1 because temperature=0 "
                "repeats the same trajectory."
            ),
        ),
    ] = 1,
    max_workers: Annotated[int, typer.Option("--max-workers")] = 1,
    runner_name: Annotated[str, typer.Option("--runner")] = "subprocess",
    out_dir: Annotated[Path | None, typer.Option("--out")] = None,
    verbose_trajectory: Annotated[bool, typer.Option("--verbose-trajectory")] = False,
    temperature: Annotated[float, typer.Option("--temperature")] = 0.0,
    yes: Annotated[bool, typer.Option("--yes")] = False,
    max_cost_usd: Annotated[float | None, typer.Option("--max-cost-usd")] = None,
    tier: Annotated[int | None, typer.Option("--tier")] = None,
    tags: Annotated[list[str] | None, typer.Option("--tag")] = None,
) -> None:
    """Run a resumable step-budget sweep."""
    del max_workers
    budgets = _parse_int_csv(max_steps_csv)
    tasks = filter_tasks(discover_tasks(tasks_dir), tier=tier, tags=tags)
    planned = planned_sweep_episodes(
        task_count=len(tasks),
        budgets=budgets,
        n_samples=n_samples,
    )
    total_episodes = sum(planned.values())
    estimated = estimate_sweep_cost(
        task_count=len(tasks),
        budgets=budgets,
        n_samples=n_samples,
        cost_per_episode_usd=MEASURED_COST_PER_EPISODE_USD,
    )
    typer.echo("MAX_STEPS\tEPISODES\tPROJECTED_COST")
    for budget, episodes in planned.items():
        typer.echo(f"{budget}\t{episodes}\t${episodes * MEASURED_COST_PER_EPISODE_USD:.4f}")
    typer.echo(f"TOTAL\t{total_episodes}\t${estimated:.4f}")
    if total_episodes > 20 and not yes:
        raise typer.BadParameter("episode count exceeds threshold; pass --yes to proceed")
    output = out_dir or Path("runs") / f"sweep-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    report = run_sweep(
        tasks=tasks,
        policy_factory=_policy_factory(policy_name, temperature=temperature),
        runner_factory=lambda: _runner(runner_name),
        budgets=budgets,
        n_samples=n_samples,
        out_dir=output,
        policy_name=policy_name,
        max_cost_usd=max_cost_usd,
        verbose_trajectory=verbose_trajectory,
    )
    typer.echo(sweep_report(report))


@app.command()
def report(
    run_dirs: Annotated[list[Path] | None, typer.Argument()] = None,
    out: Annotated[Path | None, typer.Option("--out")] = None,
) -> None:
    """Render saved evaluation reports or write a Markdown analysis report."""
    paths = _report_paths(run_dirs or [])
    if out is None and len(paths) == 1:
        typer.echo(report_table(read_report(paths[0])))
        return
    markdown = generate_report_markdown(paths)
    if out is None:
        typer.echo(markdown)
        return
    out.write_text(markdown, encoding="utf-8")
    typer.echo(f"wrote {out}")


@app.command()
def view(trajectory_jsonl: Path, out: Annotated[Path, typer.Option("--out")]) -> None:
    """Generate a self-contained HTML trajectory viewer."""
    write_viewer(trajectory_jsonl, out)
    typer.echo(f"wrote {out}")


@app.command()
def verify(
    tasks_dir: Path,
    task_id: Annotated[str | None, typer.Option("--task")] = None,
    runner_name: Annotated[str, typer.Option("--runner")] = "subprocess",
    tier: Annotated[int | None, typer.Option("--tier")] = None,
    tags: Annotated[list[str] | None, typer.Option("--tag")] = None,
) -> None:
    """Verify task quality checks for CI."""
    tasks = filter_tasks(discover_tasks(tasks_dir), tier=tier, tags=tags)
    if task_id is not None:
        tasks = [task for task in tasks if task.id == task_id]
    if not tasks:
        raise typer.BadParameter("no tasks matched")
    runner = _runner(runner_name)
    failures = 0
    typer.echo("TASK\tCHECK\tSTATUS\tDETAIL")
    for task in tasks:
        verification = verify_task(task, runner)
        for check in verification.checks:
            status = "OK" if check.passed else "FAIL"
            failures += 0 if check.passed else 1
            typer.echo(f"{task.id}\t{check.name}\t{status}\t{check.message}")
    if failures:
        raise typer.Exit(code=1)


def _find_task(task_id: str) -> TaskSpec:
    for task in discover_tasks(Path("tasks")):
        if task.id == task_id:
            return task
    raise typer.BadParameter(f"task not found: {task_id}")


def _runner(runner_name: str) -> SubprocessRunner | DockerRunner:
    if runner_name == "subprocess":
        return SubprocessRunner()
    if runner_name == "docker":
        return DockerRunner()
    raise typer.BadParameter("runner must be one of: subprocess, docker")


def _policy_factory(policy_name: str, *, temperature: float = 0.0) -> Callable[[int], Policy]:
    def factory(seed: int) -> Policy:
        if policy_name == "scripted":
            return ScriptedPolicy()
        if policy_name == "random":
            return RandomPolicy(seed=seed)
        if policy_name == "claude":
            return ClaudePolicy(temperature=temperature)
        raise typer.BadParameter("policy must be one of: scripted, random, claude")

    return factory


def _default_run_trajectory(*, task_id: str, seed: int) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return Path("runs") / timestamp / f"{task_id}-{seed}.jsonl"


def _estimated_cost_range(policy_name: str, episodes: int) -> tuple[float, float]:
    if policy_name != "claude":
        return 0.0, 0.0
    return episodes * 0.001, episodes * 0.05


def _echo_error(message: str) -> int:
    typer.echo(message, err=True)
    return 1


def _report_paths(run_dirs: list[Path]) -> list[Path]:
    if run_dirs:
        return [path / "report.json" if path.is_dir() else path for path in run_dirs]
    return discover_report_paths(Path("runs"))


def _parse_int_csv(value: str) -> list[int]:
    try:
        parsed = [int(item.strip()) for item in value.split(",") if item.strip()]
    except ValueError as exc:
        raise typer.BadParameter("--max-steps must be a comma-separated integer list") from exc
    if not parsed:
        raise typer.BadParameter("--max-steps must include at least one value")
    return parsed


if __name__ == "__main__":
    app()
