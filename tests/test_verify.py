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


def test_verify_warns_when_pristine_reward_exceeds_threshold(tmp_path: Path) -> None:
    """A partial pristine reward is visible as a warning, not a hard failure."""
    task_dir = tmp_path / "partial-pristine"
    (task_dir / "workspace").mkdir(parents=True)
    (task_dir / "solution").mkdir()
    (task_dir / "tests").mkdir()
    (task_dir / "workspace" / "client.py").write_text("VALUE = 1\n", encoding="utf-8")
    (task_dir / "solution" / "client.py").write_text("VALUE = 2\n", encoding="utf-8")
    (task_dir / "tests" / "test_hidden.py").write_text(
        "from client import VALUE\n\n"
        "def test_already_passes() -> None:\n    assert VALUE >= 1\n\n"
        "def test_needs_solution() -> None:\n    assert VALUE == 2\n",
        encoding="utf-8",
    )
    (task_dir / "task.yaml").write_text(
        """
id: partial-pristine
title: Partial Pristine
workspace: workspace
solution: solution
tests:
  visible: []
  hidden:
    - tests/test_hidden.py
reward:
  type: test_pass_ratio
""",
        encoding="utf-8",
    )

    verification = verify_task(
        load_task(task_dir),
        SubprocessRunner(),
        pristine_reward_warning_threshold=0.0,
    )
    check = {item.name: item for item in verification.checks}["fails_initially"]

    assert verification.pristine_reward == 0.5
    assert check.passed is True
    assert check.level == "warning"


def test_perf_regression_pristine_reward_is_zero() -> None:
    """The performance task no longer gives pristine hidden partial credit."""
    verification = verify_task(load_task(Path("tasks/perf-regression")), SubprocessRunner())

    assert verification.pristine_reward == 0.0


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
