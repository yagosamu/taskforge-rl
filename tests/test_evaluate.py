"""Tests for evaluation runner behavior."""

from __future__ import annotations

from pathlib import Path

from taskforge.actions import Action, ListFiles
from taskforge.env import Observation
from taskforge.evaluate import read_report, run_episode, run_eval
from taskforge.loader import discover_tasks, load_task
from taskforge.policies.base import PolicyStats
from taskforge.policies.scripted import ScriptedPolicy
from taskforge.runners import SubprocessRunner


class NeverFinishPolicy:
    """Policy that waits for the environment step limit."""

    name = "never_finish"

    def reset(self) -> None:
        """Reset policy state."""

    def act(self, obs: Observation) -> Action:
        """Keep taking intermediate actions until the environment terminates."""
        del obs
        return ListFiles(path=".")

    def stats(self) -> PolicyStats:
        """Return zero-cost policy stats."""
        return PolicyStats()


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


def test_run_eval_uses_task_limits_max_steps_over_budget_default(tmp_path: Path) -> None:
    """Eval uses the task's declared step budget, not a hardcoded default."""
    task_dir = tmp_path / "limit-task"
    (task_dir / "workspace").mkdir(parents=True)
    (task_dir / "tests").mkdir()
    (task_dir / "workspace" / "client.py").write_text("", encoding="utf-8")
    (task_dir / "tests" / "test_hidden.py").write_text(
        "def test_hidden() -> None:\n    assert True\n",
        encoding="utf-8",
    )
    (task_dir / "task.yaml").write_text(
        """
id: limit-task
title: Limit Task
workspace: workspace
tests:
  visible: []
  hidden:
    - tests/test_hidden.py
reward:
  type: test_pass_ratio
budget:
  max_steps: 3
limits:
  max_steps: 5
""",
        encoding="utf-8",
    )
    task = load_task(task_dir)

    report = run_eval(
        [task],
        lambda seed: NeverFinishPolicy(),
        n_samples=1,
        max_workers=1,
        runner_factory=SubprocessRunner,
        out_dir=tmp_path / "eval",
    )

    assert report.results[0].done_reason == "step_limit"
    assert report.results[0].steps == 5


def test_run_eval_max_steps_override_is_explicit(tmp_path: Path) -> None:
    """An explicit max_steps override wins over the task value."""
    task_dir = tmp_path / "override-task"
    (task_dir / "workspace").mkdir(parents=True)
    (task_dir / "tests").mkdir()
    (task_dir / "tests" / "test_hidden.py").write_text(
        "def test_hidden() -> None:\n    assert True\n",
        encoding="utf-8",
    )
    (task_dir / "task.yaml").write_text(
        """
id: override-task
title: Override Task
workspace: workspace
tests:
  visible: []
  hidden:
    - tests/test_hidden.py
reward:
  type: test_pass_ratio
limits:
  max_steps: 5
""",
        encoding="utf-8",
    )
    task = load_task(task_dir)

    report = run_eval(
        [task],
        lambda seed: NeverFinishPolicy(),
        n_samples=1,
        max_workers=1,
        runner_factory=SubprocessRunner,
        out_dir=tmp_path / "eval-override",
        max_steps=2,
    )

    assert report.results[0].done_reason == "step_limit"
    assert report.results[0].steps == 2


def test_run_episode_and_run_eval_share_task_step_limit(tmp_path: Path) -> None:
    """Single-run and eval paths produce the same result for the same task and policy."""
    task = load_task(Path("tasks/fix-retry-backoff"))

    single = run_episode(
        task=task,
        policy=NeverFinishPolicy(),
        runner=SubprocessRunner(),
        seed=0,
        trajectory_path=tmp_path / "single.jsonl",
    )
    report = run_eval(
        tasks=[task],
        policy_factory=lambda seed: NeverFinishPolicy(),
        n_samples=1,
        max_workers=1,
        runner_factory=SubprocessRunner,
        out_dir=tmp_path / "eval",
    )
    evaluated = report.results[0]

    assert single.reward == evaluated.reward
    assert single.steps == evaluated.steps == 25
    assert single.done_reason == evaluated.done_reason == "step_limit"
