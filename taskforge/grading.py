"""Test execution and reward calculation."""

from __future__ import annotations

import re
import sys
from collections.abc import Callable
from pathlib import Path

from taskforge.models import RewardBreakdown, TaskSpec, TestReport
from taskforge.runners import Runner

RewardFn = Callable[[TaskSpec, TestReport], RewardBreakdown]
REWARD_REGISTRY: dict[str, RewardFn] = {}


def register_reward(name: str) -> Callable[[RewardFn], RewardFn]:
    """Register a reward function by name."""

    def decorator(func: RewardFn) -> RewardFn:
        REWARD_REGISTRY[name] = func
        return func

    return decorator


def run_pytest(
    runner: Runner,
    workspace: Path,
    files: list[Path | str],
    timeout_s: int = 20,
) -> TestReport:
    """Run pytest for selected files and parse a robust test report."""
    args = [str(file) for file in files]
    result = runner.exec(
        [sys.executable, "-m", "pytest", "-vv", "-p", "no:cacheprovider", *args],
        cwd=workspace,
        timeout_s=timeout_s,
    )
    output = f"{result.stdout}\n{result.stderr}"
    counts = _parse_pytest_counts(output)
    total = counts["passed"] + counts["failed"] + counts["errors"]
    return TestReport(
        total=total,
        passed=counts["passed"],
        failed=counts["failed"],
        errors=counts["errors"],
        skipped=counts["skipped"],
        returncode=result.returncode,
        stdout=result.stdout,
        stderr=result.stderr,
        timed_out=result.timed_out,
        results=_parse_pytest_results(output),
    )


def grade(task: TaskSpec, workspace: Path, runner: Runner) -> RewardBreakdown:
    """Restore hidden tests, run them, and calculate the task reward."""
    from taskforge.workspace import restore_tests

    restore_tests(task, workspace, include_visible=False, include_hidden=True)
    hidden_files = [Path(test).relative_to(task.root) for test in task.hidden_test_paths]
    report = run_pytest(runner, workspace, hidden_files, timeout_s=task.budget.test_timeout_s)
    return REWARD_REGISTRY[task.reward.type](task, report)


@register_reward("test_pass_ratio")
def test_pass_ratio(task: TaskSpec, report: TestReport) -> RewardBreakdown:
    """Score hidden tests as passed divided by total, optionally all-or-nothing."""
    if report.total == 0:
        reward = 0.0
        reason = "No hidden tests passed; pytest did not report any runnable tests."
    elif task.reward.partial_credit:
        reward = report.passed / report.total
        reason = f"Passed {report.passed}/{report.total} hidden tests."
    else:
        reward = 1.0 if report.passed == report.total else 0.0
        reason = f"All-or-nothing score: passed {report.passed}/{report.total} hidden tests."
    return RewardBreakdown(
        reward=reward,
        components={
            "passed": float(report.passed),
            "total": float(report.total),
            "pass_ratio": reward if report.total else 0.0,
            **{
                f"test:{name}": 1.0 if outcome == "passed" else 0.0
                for name, outcome in sorted(report.results.items())
            },
        },
        reason=reason,
        report=report,
    )


def _parse_pytest_counts(output: str) -> dict[str, int]:
    counts = {"passed": 0, "failed": 0, "errors": 0, "skipped": 0}
    patterns = {
        "passed": r"(\d+) passed",
        "failed": r"(\d+) failed",
        "errors": r"(\d+) errors?",
        "skipped": r"(\d+) skipped",
    }
    for key, pattern in patterns.items():
        matches = re.findall(pattern, output)
        if matches:
            counts[key] = int(matches[-1])
    if "error" in output.lower() and counts["passed"] == counts["failed"] == counts["errors"] == 0:
        counts["errors"] = 1
    return counts


def _parse_pytest_results(output: str) -> dict[str, str]:
    results: dict[str, str] = {}
    pattern = re.compile(r"^(\S+::\S+)\s+(PASSED|FAILED|ERROR|SKIPPED)\b", re.MULTILINE)
    for nodeid, outcome in pattern.findall(output):
        results[nodeid] = outcome.lower()
    return results
