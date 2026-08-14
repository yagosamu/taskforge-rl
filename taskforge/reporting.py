"""Markdown report generation for TaskForge evaluations."""

from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path

from taskforge.analysis import FailureTag, classify_episode
from taskforge.evaluate import read_report
from taskforge.loader import discover_tasks
from taskforge.metrics import EpisodeResult, EvalReport, pass_at_k
from taskforge.models import TaskSpec
from taskforge.trajectory import read_trajectory


def generate_report_markdown(report_paths: list[Path], *, tasks_dir: Path = Path("tasks")) -> str:
    """Generate deterministic Markdown from saved evaluation reports."""
    reports = [_read_report_path(path) for path in sorted(report_paths)]
    results = [result for report in reports for result in report.results]
    tasks = {task.id: task for task in discover_tasks(tasks_dir)}
    lines = [
        "# TaskForge Evaluation Report",
        "",
        "## Headline",
        "",
        _headline_table(results),
        "",
        "## By Difficulty",
        "",
        _breakdown_table(
            "Difficulty",
            results,
            {task_id: task.metadata.difficulty for task_id, task in tasks.items()},
        ),
        "",
        "## By Tier",
        "",
        _breakdown_table(
            "Tier",
            results,
            {task_id: str(task.metadata.tier) for task_id, task in tasks.items()},
        ),
        "",
        "## By Tag",
        "",
        _tag_table(results, tasks),
        "",
        "## Per Task",
        "",
        _per_task_table(results, tasks),
        "",
        "## Failure Tags",
        "",
        _failure_table(results),
        "",
        "## Cost Summary",
        "",
        _cost_summary(results),
        "",
    ]
    return "\n".join(lines)


def discover_report_paths(root: Path = Path("runs")) -> list[Path]:
    """Discover saved report.json files under a run root."""
    if not root.exists():
        return []
    return sorted(root.glob("**/report.json"))


def _read_report_path(path: Path) -> EvalReport:
    return read_report(path)


def _headline_table(results: list[EpisodeResult]) -> str:
    rows = [
        "| Policy | pass@1 | pass@3 | Mean Reward | Mean Steps | Mean Cost |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for policy in sorted({result.policy_name for result in results}):
        subset = [result for result in results if result.policy_name == policy]
        rows.append(
            "| "
            + " | ".join(
                [
                    policy,
                    f"{_pass_at(subset, 1):.3f}",
                    f"{_pass_at(subset, 3):.3f}",
                    f"{_mean([result.reward for result in subset]):.3f}",
                    f"{_mean([result.steps for result in subset]):.2f}",
                    f"${_mean([result.cost_usd for result in subset]):.6f}",
                ]
            )
            + " |"
        )
    return "\n".join(rows)


def _breakdown_table(label_name: str, results: list[EpisodeResult], labels: dict[str, str]) -> str:
    rows = [
        f"| {label_name} | Policy | Episodes | Mean Reward | pass@1 |",
        "|---|---|---:|---:|---:|",
    ]
    keys = sorted({labels.get(result.task_id, "unspecified") for result in results})
    for key in keys:
        for policy in sorted({result.policy_name for result in results}):
            subset = [
                result
                for result in results
                if result.policy_name == policy and labels.get(result.task_id) == key
            ]
            if subset:
                rows.append(
                    f"| {key} | {policy} | {len(subset)} | "
                    f"{_mean([r.reward for r in subset]):.3f} | "
                    f"{_pass_at(subset, 1):.3f} |"
                )
    return "\n".join(rows)


def _tag_table(results: list[EpisodeResult], tasks: dict[str, TaskSpec]) -> str:
    task_tags = {task_id: task.metadata.tags for task_id, task in tasks.items()}
    rows = ["| Tag | Policy | Episodes | Mean Reward |", "|---|---|---:|---:|"]
    tags = sorted({tag for result in results for tag in task_tags.get(result.task_id, [])})
    for tag in tags:
        for policy in sorted({result.policy_name for result in results}):
            subset = [
                result
                for result in results
                if result.policy_name == policy and tag in task_tags.get(result.task_id, [])
            ]
            if subset:
                rows.append(
                    f"| {tag} | {policy} | {len(subset)} | "
                    f"{_mean([r.reward for r in subset]):.3f} |"
                )
    return "\n".join(rows)


def _per_task_table(results: list[EpisodeResult], tasks: dict[str, TaskSpec]) -> str:
    rows = [
        "| Task | Tier | Difficulty | Random Mean Reward | Claude Mean Reward |",
        "|---|---:|---|---:|---:|",
    ]
    for task_id in sorted(tasks):
        random_rewards = [
            r.reward
            for r in results
            if r.task_id == task_id and r.policy_name == "random"
        ]
        claude_rewards = [
            r.reward
            for r in results
            if r.task_id == task_id and r.policy_name == "claude"
        ]
        rows.append(
            f"| {task_id} | {tasks[task_id].metadata.tier} | "
            f"{tasks[task_id].metadata.difficulty} | "
            f"{_format_optional_mean(random_rewards)} | {_format_optional_mean(claude_rewards)} |"
        )
    return "\n".join(rows)


def _failure_table(results: list[EpisodeResult]) -> str:
    counts: Counter[FailureTag] = Counter()
    for result in results:
        if result.trajectory_path and Path(result.trajectory_path).exists():
            counts.update(classify_episode(read_trajectory(result.trajectory_path)))
    rows = ["| Failure Tag | Count |", "|---|---:|"]
    for tag, count in sorted(counts.items(), key=lambda item: (-item[1], item[0].value)):
        rows.append(f"| {tag.value} | {count} |")
    return "\n".join(rows)


def _cost_summary(results: list[EpisodeResult]) -> str:
    total = sum(result.cost_usd for result in results)
    solved = [result for result in results if result.reward >= 1.0]
    solved_cost = sum(result.cost_usd for result in solved) / len(solved) if solved else 0.0
    return "\n".join(
        [
            f"- Total cost: `${total:.6f}`",
            f"- Mean per episode: `${_mean([result.cost_usd for result in results]):.6f}`",
            f"- Mean per solved episode: `${solved_cost:.6f}`",
        ]
    )


def _pass_at(results: list[EpisodeResult], k: int) -> float:
    by_task: dict[str, list[EpisodeResult]] = defaultdict(list)
    for result in results:
        by_task[result.task_id].append(result)
    values = [
        pass_at_k(len(task_results), sum(1 for result in task_results if result.reward >= 1.0), k)
        for task_results in by_task.values()
    ]
    return _mean(values)


def _mean(values: list[float | int]) -> float:
    return float(sum(values) / len(values)) if values else 0.0


def _format_optional_mean(values: list[float]) -> str:
    return f"{_mean(values):.3f}" if values else "n/a"
