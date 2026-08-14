"""Tests for step-budget sweep aggregation and cost controls."""

from __future__ import annotations

from pathlib import Path

from taskforge.actions import Action, Finish
from taskforge.env import Observation
from taskforge.loader import load_task
from taskforge.models import TaskSpec
from taskforge.policies.base import PolicyStats
from taskforge.runners import SubprocessRunner
from taskforge.sweep import (
    SweepCell,
    SweepReport,
    estimate_sweep_cost,
    planned_sweep_episodes,
    run_sweep,
    sweep_report,
)


class FinishPolicy:
    """Policy that immediately finishes."""

    name = "finish"

    def __init__(self, *, cost_usd: float = 0.0) -> None:
        """Create the policy."""
        self.cost_usd = cost_usd

    def reset(self) -> None:
        """Reset policy state."""

    def act(self, obs: Observation) -> Action:
        """Finish immediately."""
        del obs
        return Finish()

    def stats(self) -> PolicyStats:
        """Return configured cost."""
        return PolicyStats(cost_usd=self.cost_usd)


def test_sweep_aggregation_for_fake_policy(tmp_path: Path) -> None:
    """Sweep markdown aggregates pass@1 by budget."""
    tasks = [
        _write_task(tmp_path / "pass-task", task_id="pass-task", hidden_assertion="True"),
        _write_task(tmp_path / "fail-task", task_id="fail-task", hidden_assertion="False"),
    ]

    report = run_sweep(
        tasks=tasks,
        policy_factory=lambda seed: FinishPolicy(),
        runner_factory=SubprocessRunner,
        budgets=[1, 2],
        n_samples=1,
        out_dir=tmp_path / "sweep",
    )
    markdown = sweep_report(report)

    assert "| 1 | 2/2 | 0.500 | 0.500 |" in markdown
    assert "| 2 | 2/2 | 0.500 | 0.500 |" in markdown


def test_sweep_cost_estimate_uses_configured_rate() -> None:
    """Sweep cost estimate is planned episodes times configured rate."""
    planned = planned_sweep_episodes(task_count=5, budgets=[3, 5, 25], n_samples=2)

    assert planned == {3: 10, 5: 10, 25: 10}
    assert estimate_sweep_cost(
        task_count=5,
        budgets=[3, 5, 25],
        n_samples=2,
        cost_per_episode_usd=0.055,
    ) == 1.65


def test_resuming_sweep_launches_only_missing_cells(tmp_path: Path) -> None:
    """Existing completed cells are reused on resume."""
    task = _write_task(tmp_path / "resume-task", task_id="resume-task", hidden_assertion="True")
    launch_count = 0

    def factory(seed: int) -> FinishPolicy:
        nonlocal launch_count
        launch_count += 1
        return FinishPolicy()

    run_sweep(
        tasks=[task],
        policy_factory=factory,
        runner_factory=SubprocessRunner,
        budgets=[1],
        n_samples=2,
        out_dir=tmp_path / "resume",
    )
    run_sweep(
        tasks=[task],
        policy_factory=factory,
        runner_factory=SubprocessRunner,
        budgets=[1],
        n_samples=2,
        out_dir=tmp_path / "resume",
    )

    assert launch_count == 2


def test_sweep_cost_cap_marks_remaining_cells_not_run(tmp_path: Path) -> None:
    """A global sweep cap writes a valid report with not_run cells."""
    tasks = [
        _write_task(tmp_path / "cap-a", task_id="cap-a", hidden_assertion="True"),
        _write_task(tmp_path / "cap-b", task_id="cap-b", hidden_assertion="True"),
    ]

    report = run_sweep(
        tasks=tasks,
        policy_factory=lambda seed: FinishPolicy(cost_usd=0.06),
        runner_factory=SubprocessRunner,
        budgets=[1, 2],
        n_samples=1,
        out_dir=tmp_path / "cap",
        max_cost_usd=0.05,
    )

    assert report.stopped_by_max_cost is True
    assert [cell.status for cell in report.cells].count("completed") == 1
    assert [cell.status for cell in report.cells].count("not_run") == 3
    assert (tmp_path / "cap" / "sweep.json").exists()
    assert (tmp_path / "cap" / "sweep.md").exists()


def test_sweep_report_renders_one_bar_per_budget_row() -> None:
    """Each sweep report row renders one bar for that row's value only."""
    report = SweepReport(
        policy_name="fake",
        n_samples=1,
        budgets=[3, 5, 25],
        cells=[
            _cell(task_id="a", max_steps=3, reward=0.0),
            _cell(task_id="a", max_steps=5, reward=1.0),
            _cell(task_id="a", max_steps=25, reward=1.0),
        ],
        total_cost_usd=0.0,
    )

    rows = [
        row
        for row in sweep_report(report).splitlines()
        if row.startswith("| ") and not row.startswith("| Max") and not row.startswith("|---")
    ]

    assert len(rows) == 3
    assert all(row.count("[") == 1 and row.count("]") == 1 for row in rows)


def _write_task(path: Path, *, task_id: str, hidden_assertion: str) -> TaskSpec:
    (path / "workspace").mkdir(parents=True)
    (path / "tests").mkdir()
    (path / "workspace" / "client.py").write_text("VALUE = 1\n", encoding="utf-8")
    (path / "tests" / "test_hidden.py").write_text(
        f"def test_hidden() -> None:\n    assert {hidden_assertion}\n",
        encoding="utf-8",
    )
    (path / "task.yaml").write_text(
        f"""
id: {task_id}
title: {task_id}
workspace: workspace
tests:
  visible: []
  hidden:
    - tests/test_hidden.py
reward:
  type: test_pass_ratio
limits:
  max_steps: 2
""",
        encoding="utf-8",
    )
    return load_task(path)


def _cell(*, task_id: str, max_steps: int, reward: float) -> SweepCell:
    return SweepCell(
        task_id=task_id,
        max_steps=max_steps,
        seed=max_steps,
        status="completed",
        result={
            "task_id": task_id,
            "policy_name": "fake",
            "seed": max_steps,
            "reward": reward,
            "steps": 1,
            "done_reason": "finish",
        },
    )
