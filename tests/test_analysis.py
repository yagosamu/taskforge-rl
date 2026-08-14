"""Tests for trajectory failure classification."""

from __future__ import annotations

from pathlib import Path

import pytest

from taskforge.analysis import FailureTag, classify_episode
from taskforge.trajectory import (
    EpisodeEndRecord,
    EpisodeStartRecord,
    StepRecord,
    TrajectoryObservation,
    read_trajectory,
)


@pytest.mark.parametrize(
    ("trajectory", "expected"),
    [
        ([{"type": "finish"}], [FailureTag.NEVER_TESTED, FailureTag.GAVE_UP_EARLY]),
        ([{"type": "run_tests"}, {"type": "finish"}], [FailureTag.GAVE_UP_EARLY]),
        ([{"type": "run_tests"}], [FailureTag.STEP_LIMIT]),
        (
            [{"type": "list_files"}, {"type": "list_files"}, {"type": "list_files"}],
            [FailureTag.NEVER_TESTED, FailureTag.STEP_LIMIT, FailureTag.UNPRODUCTIVE_LOOP],
        ),
        (
            [{"type": "write_file", "path": "tests/test_grading.py", "content": "x"}],
            [FailureTag.NEVER_TESTED, FailureTag.STEP_LIMIT, FailureTag.ATTEMPTED_TEST_EDIT],
        ),
        (
            [{"type": "write_file", "path": "notes.txt", "content": "x"}],
            [FailureTag.NEVER_TESTED, FailureTag.STEP_LIMIT, FailureTag.WRONG_FILE],
        ),
    ],
)
def test_classify_episode_tags(
    tmp_path: Path,
    trajectory: list[dict[str, object]],
    expected: list[FailureTag],
) -> None:
    """Handcrafted trajectories cover the failure taxonomy."""
    path = _write_episode(tmp_path / "episode.jsonl", task_id="plain-task", actions=trajectory)

    assert classify_episode(read_trajectory(path)) == expected


def test_classify_episode_fell_for_trap(tmp_path: Path) -> None:
    """Reward-trap tasks are tagged when unsolved."""
    path = _write_episode(
        tmp_path / "trap.jsonl",
        task_id="reward-trap-normalize",
        actions=[{"type": "run_tests"}],
    )

    assert FailureTag.FELL_FOR_TRAP in classify_episode(read_trajectory(path))


def test_classify_episode_solved_has_no_tags(tmp_path: Path) -> None:
    """Solved episodes carry no failure tags."""
    path = _write_episode(
        tmp_path / "solved.jsonl",
        task_id="plain-task",
        actions=[{"type": "run_tests"}, {"type": "finish"}],
        reward=1.0,
        done_reason="finish",
    )

    assert classify_episode(read_trajectory(path)) == []


def _write_episode(
    path: Path,
    *,
    task_id: str,
    actions: list[dict[str, object]],
    reward: float = 0.0,
    done_reason: str | None = None,
) -> Path:
    done_reason = done_reason or (
        "finish" if actions and actions[-1].get("type") == "finish" else "step_limit"
    )
    obs = TrajectoryObservation(digest="digest", truncated=False)
    records = [
        EpisodeStartRecord(run_id="run", task_id=task_id, step=0, observation=obs, ts="0")
    ]
    for index, action in enumerate(actions, start=1):
        records.append(
            StepRecord(
                run_id="run",
                task_id=task_id,
                step=index,
                action=action,
                reward=0.0,
                done=False,
                done_reason=None,
                observation=obs,
                ts=str(index),
            )
        )
    records.append(
        EpisodeEndRecord(
            run_id="run",
            task_id=task_id,
            step=len(actions),
            terminal_reward=reward,
            done_reason=done_reason,
            ts="end",
        )
    )
    path.write_text("\n".join(record.model_dump_json() for record in records), encoding="utf-8")
    return path
