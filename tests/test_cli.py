"""Tests for TaskForge CLI policy wiring."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from taskforge.actions import Action, Finish
from taskforge.cli import app
from taskforge.env import Observation
from taskforge.loader import load_task
from taskforge.policies.base import PolicyStats
from taskforge.trajectory import EpisodeStartRecord, read_trajectory


class DummyClaudePolicy:
    """No-network stand-in for the Claude policy in CLI tests."""

    name = "claude"

    def __init__(self, *, temperature: float = 0.0) -> None:
        """Create a dummy Claude policy."""
        self.temperature = temperature

    def reset(self) -> None:
        """Reset policy state."""

    def act(self, obs: Observation) -> Action:
        """Immediately finish."""
        del obs
        return Finish()

    def stats(self) -> PolicyStats:
        """Return zero-cost stats."""
        return PolicyStats()


def test_run_accepts_all_policy_names(monkeypatch) -> None:
    """The run command accepts every policy supported by eval."""
    import taskforge.cli as cli

    monkeypatch.setattr(cli, "ClaudePolicy", DummyClaudePolicy)
    runner = CliRunner()

    for policy_name in ["scripted", "random", "claude"]:
        result = runner.invoke(
            app,
            [
                "run",
                "fix-retry-backoff",
                "--policy",
                policy_name,
                "--runner",
                "subprocess",
                "--max-steps",
                "1",
            ],
        )

        assert result.exit_code == 0, result.output


def test_run_writes_default_trajectory(monkeypatch) -> None:
    """The run command writes a trajectory even when --trajectory is omitted."""
    import taskforge.cli as cli

    monkeypatch.setattr(cli, "ClaudePolicy", DummyClaudePolicy)
    result = CliRunner().invoke(
        app,
        [
            "run",
            "fix-retry-backoff",
            "--policy",
            "random",
            "--runner",
            "subprocess",
            "--max-steps",
            "1",
        ],
    )

    assert result.exit_code == 0, result.output
    assert '"trajectory_path": null' not in result.output
    marker = '"trajectory_path": "'
    trajectory_path = Path(result.output.split(marker)[1].split('"')[0])
    assert trajectory_path.is_file()


def test_claude_temperature_is_recorded_in_episode_header(monkeypatch, tmp_path: Path) -> None:
    """Claude temperature flows from CLI into the trajectory episode_start metadata."""
    import taskforge.cli as cli

    monkeypatch.setattr(cli, "ClaudePolicy", DummyClaudePolicy)
    trajectory = tmp_path / "claude.jsonl"
    result = CliRunner().invoke(
        app,
        [
            "run",
            "fix-retry-backoff",
            "--policy",
            "claude",
            "--runner",
            "subprocess",
            "--trajectory",
            str(trajectory),
            "--temperature",
            "0.7",
        ],
    )

    assert result.exit_code == 0, result.output
    start = read_trajectory(trajectory).records[0]
    assert isinstance(start, EpisodeStartRecord)
    assert start.metadata["policy_name"] == "claude"
    assert start.metadata["seed"] == 0
    assert start.metadata["temperature"] == 0.7


def test_load_task_exposes_fix_retry_backoff_max_steps() -> None:
    """The example task declares its canonical step budget in limits.max_steps."""
    task = load_task(Path("tasks/fix-retry-backoff"))

    assert task.max_steps == 25
    assert task.limits.max_steps == 25
