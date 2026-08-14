"""Tests for trajectory writing, reading, and replay determinism."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from taskforge.actions import Finish, RunTests
from taskforge.cli import app
from taskforge.env import TaskEnv
from taskforge.loader import load_task
from taskforge.trajectory import StepRecord, read_trajectory


def test_trajectory_round_trips_and_replay_matches(tmp_path: Path) -> None:
    """A trajectory can be parsed and replayed with the same terminal reward."""
    task = load_task(Path("tasks/fix-retry-backoff"))
    trajectory = tmp_path / "trajectory.jsonl"

    with TaskEnv(task, trajectory_path=trajectory, verbose_trajectory=True) as env:
        env.reset()
        env.step(RunTests())
        final = env.step(Finish())

    episode = read_trajectory(trajectory)
    assert episode.terminal_reward == final.reward
    assert any(isinstance(record, StepRecord) for record in episode.records)
    assert (tmp_path / "trajectory.jsonl.observations.jsonl").exists()

    result = CliRunner().invoke(app, ["replay", str(trajectory)])

    assert result.exit_code == 0
    assert "replay ok" in result.stdout
