"""Command line interface for TaskForge."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Annotated

import typer

from taskforge.actions import Finish, RunTests, parse_action
from taskforge.env import TaskEnv
from taskforge.evaluate import read_report, report_table, run_eval
from taskforge.loader import discover_tasks, load_task
from taskforge.models import TaskSpec, TaskValidationError
from taskforge.policies.base import Policy
from taskforge.policies.claude import ClaudePolicy
from taskforge.policies.random_policy import RandomPolicy
from taskforge.policies.scripted import ScriptedPolicy
from taskforge.runners import DockerRunner, SubprocessRunner
from taskforge.trajectory import read_trajectory, summarize_episode

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
) -> None:
    """Run a task with a hardcoded policy and print the reward breakdown."""
    if policy != "scripted":
        raise typer.BadParameter("only --policy scripted is implemented")
    task = _find_task(task_id)
    runner = _runner(runner_name)
    with TaskEnv(
        task,
        runner=runner,
        trajectory_path=trajectory,
        verbose_trajectory=verbose_trajectory,
    ) as env:
        env.reset()
        env.step(RunTests())
        result = env.step(Finish())
    breakdown = result.info.get("reward_breakdown")
    typer.echo(breakdown)


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
        tasks,
        _policy_factory(policy_name),
        n_samples,
        max_workers,
        runner_factory=lambda: _runner(runner_name),
        out_dir=output,
        max_cost_usd=max_cost_usd,
    )
    typer.echo(report_table(report))


@app.command()
def report(run_dir: Path) -> None:
    """Render a saved evaluation report."""
    typer.echo(report_table(read_report(run_dir)))


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


def _policy_factory(policy_name: str) -> Callable[[int], Policy]:
    def factory(seed: int) -> Policy:
        if policy_name == "scripted":
            return ScriptedPolicy()
        if policy_name == "random":
            return RandomPolicy(seed=seed)
        if policy_name == "claude":
            return ClaudePolicy()
        raise typer.BadParameter("policy must be one of: scripted, random, claude")

    return factory


def _estimated_cost_range(policy_name: str, episodes: int) -> tuple[float, float]:
    if policy_name != "claude":
        return 0.0, 0.0
    return episodes * 0.001, episodes * 0.05


def _echo_error(message: str) -> int:
    typer.echo(message, err=True)
    return 1


if __name__ == "__main__":
    app()
