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
from taskforge.loader import discover_tasks, load_task
from taskforge.models import TaskSpec, TaskValidationError
from taskforge.policies.base import Policy
from taskforge.policies.claude import ClaudePolicy
from taskforge.policies.random_policy import RandomPolicy
from taskforge.policies.scripted import ScriptedPolicy
from taskforge.runners import DockerRunner, SubprocessRunner
from taskforge.trajectory import read_trajectory, summarize_episode
from taskforge.verify import verify_task

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
) -> None:
    """Run a parallel policy evaluation and save report.json."""
    tasks = discover_tasks(tasks_dir)
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
def report(run_dir: Path) -> None:
    """Render a saved evaluation report."""
    typer.echo(report_table(read_report(run_dir)))


@app.command()
def verify(
    tasks_dir: Path,
    task_id: Annotated[str | None, typer.Option("--task")] = None,
    runner_name: Annotated[str, typer.Option("--runner")] = "subprocess",
) -> None:
    """Verify task quality checks for CI."""
    tasks = discover_tasks(tasks_dir)
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


if __name__ == "__main__":
    app()
