"""End-to-end environment tests."""

from __future__ import annotations

import json
from pathlib import Path

from taskforge.actions import ReadFile, WriteFile
from taskforge.env import Finish, RunTests, TaskEnv
from taskforge.loader import load_task
from taskforge.trajectory import EpisodeEndRecord, StepRecord, read_trajectory


def test_full_episode_writes_well_formed_jsonl(tmp_path: Path) -> None:
    """A scripted policy can run visible tests, finish, and produce JSONL events."""
    task = load_task(Path("tasks/fix-retry-backoff"))
    event_log = tmp_path / "trajectory.jsonl"

    with TaskEnv(task, event_log_path=event_log) as env:
        first = env.reset()
        visible = env.step(RunTests())
        final = env.step(Finish())

    assert first.task_id == "fix-retry-backoff"
    assert "Fix retry final exception propagation" in first.task_statement
    assert "must re-raise the final exception" in first.task_statement
    assert visible.reward == 0.0
    assert visible.observation.task_statement == first.task_statement
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


def test_reading_missing_file_continues_and_counts_invalid_action() -> None:
    """A missing file is an invalid action, not an internal episode error."""
    task = load_task(Path("tasks/fix-retry-backoff"))

    with TaskEnv(task) as env:
        env.reset()
        result = env.step(ReadFile(path="missing.py"))

    assert result.done is False
    assert result.done_reason is None
    assert result.info["invalid_action"] is True
    assert result.info["invalid_actions"] == 1
    assert "invalid action" in result.observation.last_output


def test_writing_outside_workspace_continues_and_counts_invalid_action(tmp_path: Path) -> None:
    """A path escape is an invalid action, not an internal episode error."""
    task = load_task(Path("tasks/fix-retry-backoff"))
    outside = tmp_path / "outside.txt"

    with TaskEnv(task) as env:
        env.reset()
        result = env.step(WriteFile(path=str(outside), content="nope"))

    assert result.done is False
    assert result.done_reason is None
    assert result.info["invalid_action"] is True
    assert result.info["invalid_actions"] == 1
    assert not outside.exists()


def test_invalid_action_counter_is_written_to_trajectory(tmp_path: Path) -> None:
    """Trajectory step and end records include the invalid action count."""
    task = load_task(Path("tasks/fix-retry-backoff"))
    trajectory = tmp_path / "invalid.jsonl"

    with TaskEnv(task, trajectory_path=trajectory) as env:
        env.reset()
        env.step(ReadFile(path="missing.py"))
        env.step(Finish())

    records = read_trajectory(trajectory).records
    step_records = [record for record in records if isinstance(record, StepRecord)]
    end_record = next(record for record in records if isinstance(record, EpisodeEndRecord))
    assert step_records[0].invalid_actions == 1
    assert step_records[1].invalid_actions == 1
    assert end_record.invalid_actions == 1


def test_reset_observation_includes_task_description() -> None:
    """The first observation includes the task title and description for policies."""
    task = load_task(Path("tasks/fix-retry-backoff"))

    with TaskEnv(task) as env:
        observation = env.reset()

    assert task.title in observation.task_statement
    assert "must re-raise the final exception" in observation.task_statement
