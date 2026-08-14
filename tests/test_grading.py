"""Tests for reward calculation and grading safety."""

from __future__ import annotations

from pathlib import Path

from taskforge.grading import grade
from taskforge.grading import test_pass_ratio as reward_test_pass_ratio
from taskforge.loader import load_task
from taskforge.models import RewardSpec, TaskSpec
from taskforge.models import TestReport as TaskForgeTestReport
from taskforge.models import TestSpec as TaskForgeTestSpec
from taskforge.runners import SubprocessRunner
from taskforge.workspace import ephemeral_workspace


def _task(partial_credit: bool) -> TaskSpec:
    return TaskSpec(
        id="unit",
        title="Unit",
        root=Path("."),
        tests=TaskForgeTestSpec(visible=[], hidden=[]),
        reward=RewardSpec(type="test_pass_ratio", partial_credit=partial_credit),
    )


def test_pass_ratio_with_partial_credit() -> None:
    """Partial credit returns passed divided by total."""
    report = TaskForgeTestReport(
        total=4,
        passed=3,
        failed=1,
        errors=0,
        skipped=0,
        returncode=1,
        stdout="",
        stderr="",
    )

    breakdown = reward_test_pass_ratio(_task(partial_credit=True), report)

    assert breakdown.reward == 0.75


def test_pass_ratio_without_partial_credit() -> None:
    """All-or-nothing rewards are zero unless every hidden test passes."""
    report = TaskForgeTestReport(
        total=4,
        passed=3,
        failed=1,
        errors=0,
        skipped=0,
        returncode=1,
        stdout="",
        stderr="",
    )

    breakdown = reward_test_pass_ratio(_task(partial_credit=False), report)

    assert breakdown.reward == 0.0


def test_grade_restores_hidden_tests_before_running(tmp_path: Path) -> None:
    """Overwriting hidden tests inside the workspace does not affect grading."""
    task = load_task(Path("tasks/fix-retry-backoff"))
    runner = SubprocessRunner()

    with ephemeral_workspace(task) as workspace:
        hidden = workspace / "tests" / "test_grading.py"
        hidden.write_text(
            "def test_fake_passes() -> None:\n    assert True\n",
            encoding="utf-8",
        )
        breakdown = grade(task, workspace, runner)

    assert breakdown.reward == 0.0
    assert breakdown.report is not None
    assert breakdown.report.failed == 1


def test_example_task_scores_one_after_expected_fix() -> None:
    """The example task is solvable by re-raising the final exception."""
    task = load_task(Path("tasks/fix-retry-backoff"))
    runner = SubprocessRunner()

    with ephemeral_workspace(task) as workspace:
        client = workspace / "client.py"
        client.write_text(
            '''"""Small client helpers used by the retry task."""

from __future__ import annotations

from collections.abc import Callable
from time import sleep
from typing import TypeVar

T = TypeVar("T")


def retry(func: Callable[[], T], *, attempts: int = 3, backoff_s: float = 0.0) -> T:
    """Call a function until it succeeds or attempts are exhausted."""
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            return func()
        except Exception as exc:
            last_error = exc
            if attempt < attempts - 1 and backoff_s:
                sleep(backoff_s)
    assert last_error is not None
    raise last_error
''',
            encoding="utf-8",
        )
        breakdown = grade(task, workspace, runner)

    assert breakdown.reward == 1.0
