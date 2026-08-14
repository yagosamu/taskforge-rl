"""Tests for task verification."""

from __future__ import annotations

from pathlib import Path

import pytest

from taskforge.loader import discover_tasks, load_task
from taskforge.runners import SubprocessRunner
from taskforge.verify import verify_task


@pytest.mark.parametrize(
    ("task_id", "check_name"),
    [
        ("passes-initially", "fails_initially"),
        ("unsolvable", "solvable"),
        ("visible-fails", "visible_consistent"),
        ("leaks-hidden", "no_leakage"),
        ("nondeterministic", "deterministic"),
    ],
)
def test_verify_task_catches_bad_fixture(task_id: str, check_name: str) -> None:
    """Each deliberately bad fixture fails its targeted verification check."""
    task = load_task(Path("tests/fixtures/bad_tasks") / task_id)
    verification = verify_task(task, SubprocessRunner())
    checks = {check.name: check for check in verification.checks}

    assert checks[check_name].passed is False


@pytest.mark.slow
def test_shipped_tasks_pass_verification() -> None:
    """All shipped tasks pass the authoring verification suite."""
    failures: list[str] = []
    tasks = discover_tasks(Path("tasks"))
    tier_two = [task for task in tasks if task.metadata.tier == 2]
    for task in tasks:
        verification = verify_task(task, SubprocessRunner())
        failures.extend(
            f"{task.id}:{check.name}:{check.message}"
            for check in verification.checks
            if not check.passed
        )

    assert len(tasks) == 15
    assert len(tier_two) == 5
    assert failures == []


def test_shipped_tasks_have_non_empty_descriptions() -> None:
    """Every shipped task has a prompt description available to the agent."""
    empty = [
        task.id
        for task in discover_tasks(Path("tasks"))
        if not task.description.strip()
    ]

    assert empty == []
