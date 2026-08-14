"""Task quality verification checks."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

from taskforge.grading import grade, run_pytest
from taskforge.models import TaskSpec
from taskforge.runners import Runner
from taskforge.workspace import apply_solution, ephemeral_workspace


class VerificationCheck(BaseModel):
    """Result for one task verification check."""

    model_config = ConfigDict(extra="forbid")

    name: str
    passed: bool
    message: str
    level: Literal["ok", "warning", "error"] = "ok"
    reward: float | None = None


class TaskVerification(BaseModel):
    """Verification result for a task."""

    model_config = ConfigDict(extra="forbid")

    task_id: str
    checks: list[VerificationCheck]
    pristine_reward: float

    @property
    def passed(self) -> bool:
        """Return true when every verification check passed."""
        return all(check.passed for check in self.checks)


def verify_task(
    task: TaskSpec,
    runner: Runner,
    *,
    pristine_reward_warning_threshold: float = 0.0,
) -> TaskVerification:
    """Verify that a task is failing, solvable, leak-free, and deterministic."""
    fails_initially = _fails_initially(
        task,
        runner,
        warning_threshold=pristine_reward_warning_threshold,
    )
    checks = [
        fails_initially,
        _solvable(task, runner),
        _visible_consistent(task, runner),
        _no_leakage(task),
        _deterministic(task, runner),
    ]
    return TaskVerification(
        task_id=task.id,
        checks=checks,
        pristine_reward=fails_initially.reward or 0.0,
    )


def _fails_initially(
    task: TaskSpec,
    runner: Runner,
    *,
    warning_threshold: float,
) -> VerificationCheck:
    with ephemeral_workspace(task) as workspace:
        reward = grade(task, workspace, runner).reward
    passed = reward < 1.0
    warning = passed and reward > warning_threshold
    return VerificationCheck(
        name="fails_initially",
        passed=passed,
        message=f"initial hidden reward={reward:.3f}",
        level="warning" if warning else "ok" if passed else "error",
        reward=reward,
    )


def _solvable(task: TaskSpec, runner: Runner) -> VerificationCheck:
    try:
        with ephemeral_workspace(task) as workspace:
            apply_solution(task, workspace)
            reward = grade(task, workspace, runner).reward
    except Exception as exc:
        return VerificationCheck(name="solvable", passed=False, message=str(exc))
    return VerificationCheck(
        name="solvable",
        passed=reward == 1.0,
        message=f"solution hidden reward={reward:.3f}",
    )


def _visible_consistent(task: TaskSpec, runner: Runner) -> VerificationCheck:
    if not task.tests.visible:
        return VerificationCheck(
            name="visible_consistent",
            passed=True,
            message="no visible tests declared",
        )
    with ephemeral_workspace(task) as workspace:
        apply_solution(task, workspace)
        report = run_pytest(
            runner,
            workspace,
            [Path(test) for test in task.tests.visible],
            timeout_s=task.budget.test_timeout_s,
        )
    passed = not report.timed_out and report.returncode == 0
    return VerificationCheck(
        name="visible_consistent",
        passed=passed,
        message=f"visible passed={report.passed}/{report.total} returncode={report.returncode}",
    )


def _no_leakage(task: TaskSpec) -> VerificationCheck:
    leaks: list[str] = []
    with ephemeral_workspace(task) as workspace:
        if (workspace / "solution").exists():
            leaks.append("solution directory present")
        for hidden in task.tests.hidden:
            if (workspace / hidden).exists():
                leaks.append(f"hidden test present: {hidden}")
    return VerificationCheck(
        name="no_leakage",
        passed=not leaks,
        message="no leaks" if not leaks else "; ".join(leaks),
    )


def _deterministic(task: TaskSpec, runner: Runner) -> VerificationCheck:
    with ephemeral_workspace(task) as workspace:
        first = grade(task, workspace, runner).reward
        second = grade(task, workspace, runner).reward
    return VerificationCheck(
        name="deterministic",
        passed=first == second,
        message=f"rewards={first:.3f},{second:.3f}",
    )
