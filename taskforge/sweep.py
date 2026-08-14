"""Step-budget sweep runner and reporting."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from taskforge.evaluate import PolicyFactory, RunnerFactory, run_episode
from taskforge.metrics import EpisodeResult, pass_at_k
from taskforge.models import TaskSpec

MEASURED_COST_PER_EPISODE_USD = 0.055


class SweepCell(BaseModel):
    """One task/budget/seed sweep cell."""

    model_config = ConfigDict(extra="forbid")

    task_id: str
    max_steps: int
    seed: int
    status: str
    result: EpisodeResult | None = None


class SweepReport(BaseModel):
    """Saved sweep report."""

    model_config = ConfigDict(extra="forbid")

    policy_name: str
    n_samples: int
    budgets: list[int]
    cells: list[SweepCell]
    total_cost_usd: float
    stopped_by_max_cost: bool = False


def planned_sweep_episodes(
    *,
    task_count: int,
    budgets: Sequence[int],
    n_samples: int,
) -> dict[int, int]:
    """Return planned episode counts per budget."""
    return {budget: task_count * n_samples for budget in budgets}


def estimate_sweep_cost(
    *,
    task_count: int,
    budgets: Sequence[int],
    n_samples: int,
    cost_per_episode_usd: float = MEASURED_COST_PER_EPISODE_USD,
) -> float:
    """Estimate sweep cost using a measured per-episode rate."""
    return sum(planned_sweep_episodes(
        task_count=task_count,
        budgets=budgets,
        n_samples=n_samples,
    ).values()) * cost_per_episode_usd


def run_sweep(
    *,
    tasks: Sequence[TaskSpec],
    policy_factory: PolicyFactory,
    runner_factory: RunnerFactory,
    budgets: Sequence[int],
    n_samples: int,
    out_dir: Path,
    policy_name: str | None = None,
    max_cost_usd: float | None = None,
    verbose_trajectory: bool = False,
) -> SweepReport:
    """Run or resume a step-budget sweep."""
    out_dir.mkdir(parents=True, exist_ok=True)
    existing = _load_existing(out_dir / "sweep.json")
    resolved_policy_name = existing.policy_name if existing else policy_name or "unknown"
    completed = {
        (cell.task_id, cell.max_steps, cell.seed): cell
        for cell in (existing.cells if existing else [])
        if cell.status == "completed"
    }
    cells: list[SweepCell] = []
    total_cost = sum(
        cell.result.cost_usd
        for cell in completed.values()
        if cell.result is not None
    )
    stopped = bool(existing and existing.stopped_by_max_cost)

    for budget in budgets:
        for task in sorted(tasks, key=lambda item: item.id):
            for sample in range(n_samples):
                seed = _seed_for(task, budget, sample)
                key = (task.id, budget, seed)
                if key in completed:
                    cells.append(completed[key])
                    continue
                if max_cost_usd is not None and total_cost >= max_cost_usd:
                    stopped = True
                    cells.append(_not_run(task_id=task.id, max_steps=budget, seed=seed))
                    continue
                trajectory = out_dir / f"{task.id}-steps{budget}-seed{seed}.jsonl"
                result = run_episode(
                    task=task,
                    policy=policy_factory(seed),
                    runner=runner_factory(),
                    seed=seed,
                    trajectory_path=trajectory,
                    verbose_trajectory=verbose_trajectory,
                    max_steps=budget,
                )
                total_cost += result.cost_usd
                cells.append(
                    SweepCell(
                        task_id=task.id,
                        max_steps=budget,
                        seed=seed,
                        status="completed",
                        result=result,
                    )
                )

    report = SweepReport(
        policy_name=resolved_policy_name,
        n_samples=n_samples,
        budgets=list(budgets),
        cells=sorted(cells, key=lambda cell: (cell.max_steps, cell.task_id, cell.seed)),
        total_cost_usd=total_cost,
        stopped_by_max_cost=stopped,
    )
    (out_dir / "sweep.json").write_text(report.model_dump_json(indent=2), encoding="utf-8")
    (out_dir / "sweep.md").write_text(sweep_report(report), encoding="utf-8")
    return report


def read_sweep(path: Path | str) -> SweepReport:
    """Read a sweep report from a directory or JSON file."""
    report_path = Path(path)
    if report_path.is_dir():
        report_path = report_path / "sweep.json"
    return SweepReport.model_validate_json(report_path.read_text(encoding="utf-8"))


def sweep_report(report: SweepReport) -> str:
    """Render deterministic Markdown with pass@1 by step budget."""
    rows = ["| Max Steps | Completed | pass@1 | Mean Reward | Curve |", "|---:|---:|---:|---:|---|"]
    values: list[float] = []
    for budget in report.budgets:
        cells = [cell for cell in report.cells if cell.max_steps == budget]
        completed = [cell for cell in cells if cell.result is not None]
        pass_1 = _pass_at_budget(completed, 1)
        mean_reward = _mean([cell.result.reward for cell in completed if cell.result])
        values.append(pass_1)
        rows.append(
            f"| {budget} | {len(completed)}/{len(cells)} | {pass_1:.3f} | "
            f"{mean_reward:.3f} | {sparkline(values)} |"
        )
    rows.extend(
        [
            "",
            f"Total cost: `${report.total_cost_usd:.6f}`",
            f"Stopped by max cost: `{str(report.stopped_by_max_cost).lower()}`",
        ]
    )
    return "\n".join(rows)


def sparkline(values: Sequence[float]) -> str:
    """Render a tiny ASCII sparkline for values in [0, 1]."""
    if not values:
        return ""
    bars = []
    width = 10
    for value in values:
        filled = min(round(value * width), width)
        bars.append("[" + ("#" * filled).ljust(width, "-") + "]")
    return " ".join(bars)


def _load_existing(path: Path) -> SweepReport | None:
    if not path.exists():
        return None
    return read_sweep(path)


def _not_run(*, task_id: str, max_steps: int, seed: int) -> SweepCell:
    return SweepCell(task_id=task_id, max_steps=max_steps, seed=seed, status="not_run")


def _seed_for(task: TaskSpec, budget: int, sample: int) -> int:
    del task
    return budget * 10_000 + sample


def _pass_at_budget(cells: list[SweepCell], k: int) -> float:
    by_task: dict[str, list[SweepCell]] = defaultdict(list)
    for cell in cells:
        by_task[cell.task_id].append(cell)
    values = []
    for task_cells in by_task.values():
        rewards = [cell.result.reward for cell in task_cells if cell.result is not None]
        values.append(pass_at_k(len(rewards), sum(1 for reward in rewards if reward >= 1.0), k))
    return _mean(values)


def _mean(values: Sequence[float]) -> float:
    return float(sum(values) / len(values)) if values else 0.0
