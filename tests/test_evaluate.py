"""Tests for evaluation runner behavior."""

from __future__ import annotations

from pathlib import Path

from taskforge.evaluate import read_report, run_eval
from taskforge.loader import discover_tasks
from taskforge.policies.scripted import ScriptedPolicy
from taskforge.runners import SubprocessRunner


def test_run_eval_scripted_policy_writes_report(tmp_path: Path) -> None:
    """Scripted evaluation produces a well-formed saved report."""
    tasks = discover_tasks(Path("tasks"))
    report = run_eval(
        tasks,
        lambda seed: ScriptedPolicy(),
        n_samples=2,
        max_workers=1,
        runner_factory=SubprocessRunner,
        out_dir=tmp_path,
    )

    saved = read_report(tmp_path)
    assert saved == report
    assert report.policy_name == "scripted"
    assert len(report.results) == 2
    assert report.mean_reward == 0.0
    assert report.done_reasons == {"finish": 2}
    assert (tmp_path / "report.json").exists()


def test_parallel_eval_matches_serial_results(tmp_path: Path) -> None:
    """Parallel execution produces the same per-task outcomes as serial execution."""
    tasks = discover_tasks(Path("tasks"))
    serial = run_eval(
        tasks,
        lambda seed: ScriptedPolicy(),
        n_samples=3,
        max_workers=1,
        runner_factory=SubprocessRunner,
        out_dir=tmp_path / "serial",
    )
    parallel = run_eval(
        tasks,
        lambda seed: ScriptedPolicy(),
        n_samples=3,
        max_workers=3,
        runner_factory=SubprocessRunner,
        out_dir=tmp_path / "parallel",
    )

    serial_outcomes = [
        (result.task_id, result.seed, result.reward, result.steps, result.done_reason)
        for result in serial.results
    ]
    parallel_outcomes = [
        (result.task_id, result.seed, result.reward, result.steps, result.done_reason)
        for result in parallel.results
    ]
    assert parallel_outcomes == serial_outcomes


def test_verbose_trajectory_writes_one_side_file_per_parallel_episode(tmp_path: Path) -> None:
    """Verbose parallel eval writes full observations beside each trajectory."""
    tasks = discover_tasks(Path("tasks"))
    report = run_eval(
        tasks,
        lambda seed: ScriptedPolicy(),
        n_samples=2,
        max_workers=2,
        runner_factory=SubprocessRunner,
        out_dir=tmp_path,
        verbose_trajectory=True,
    )

    side_files = sorted(tmp_path.glob("*.jsonl.observations.jsonl"))
    trajectory_paths = {Path(result.trajectory_path or "") for result in report.results}
    side_trajectories = {
        side_file.with_name(side_file.name.removesuffix(".observations.jsonl"))
        for side_file in side_files
    }

    assert len(side_files) == 2
    assert side_trajectories == trajectory_paths
    assert all(side_file.read_text(encoding="utf-8").strip() for side_file in side_files)
