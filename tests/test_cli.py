"""Tests for TaskForge CLI policy wiring."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from taskforge.actions import Action, Finish
from taskforge.cli import app
from taskforge.env import Observation
from taskforge.loader import load_task
from taskforge.policies.base import PolicyStats


class DummyClaudePolicy:
    """No-network stand-in for the Claude policy in CLI tests."""

    name = "claude"

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


def test_load_task_exposes_fix_retry_backoff_max_steps() -> None:
    """The example task declares its canonical step budget in limits.max_steps."""
    task = load_task(Path("tasks/fix-retry-backoff"))

    assert task.max_steps == 25
    assert task.limits.max_steps == 25
