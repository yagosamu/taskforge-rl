"""End-to-end environment tests."""

from __future__ import annotations

import json
from pathlib import Path

from taskforge.env import Finish, RunTests, TaskEnv
from taskforge.loader import load_task


def test_full_episode_writes_well_formed_jsonl(tmp_path: Path) -> None:
    """A scripted policy can run visible tests, finish, and produce JSONL events."""
    task = load_task(Path("tasks/fix-retry-backoff"))
    event_log = tmp_path / "trajectory.jsonl"

    with TaskEnv(task, event_log_path=event_log) as env:
        first = env.reset()
        visible = env.step(RunTests())
        final = env.step(Finish())

    assert first.task_id == "fix-retry-backoff"
    assert visible.reward == 0.0
    assert final.done is True
    assert final.reward == 0.0

    lines = event_log.read_text(encoding="utf-8").splitlines()
    events = [json.loads(line) for line in lines]
    assert [event["event_type"] for event in events] == ["reset", "step", "step", "reward"]
    for event in events:
        assert event["run_id"]
        assert event["task_id"] == "fix-retry-backoff"
        assert isinstance(event["step"], int)
        assert event["ts"]
