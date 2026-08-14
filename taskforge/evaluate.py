"""Parallel evaluation runner for TaskForge policies."""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from pathlib import Path

from taskforge.env import TaskEnv
from taskforge.metrics import EpisodeResult, EvalReport, aggregate_results
from taskforge.models import TaskSpec
from taskforge.policies.base import Policy
from taskforge.runners import Runner

PolicyFactory = Callable[[int], Policy]
RunnerFactory = Callable[[], Runner]


def run_episode(
    task: TaskSpec,
    policy: Policy,
    runner: Runner,
    seed: int,
    *,
    trajectory_path: Path | None = None,
    verbose_trajectory: bool = False,
) -> EpisodeResult:
    """Run one task episode and return a structured result."""
    policy.reset()
    with TaskEnv(
        task,
        runner=runner,
        trajectory_path=trajectory_path,
        verbose_trajectory=verbose_trajectory,
    ) as env:
        obs = env.reset()
        result = None
        try:
            while True:
                action = policy.act(obs)
                result = env.step(action)
                obs = result.observation
                if result.done:
                    break
        except Exception as exc:
            result = env.abort("error", str(exc))
            error = str(exc)
        else:
            error = None
    stats = policy.stats()
    assert result is not None
    return EpisodeResult(
        task_id=task.id,
        policy_name=policy.name,
        seed=seed,
        reward=result.reward,
        steps=result.observation.step,
        done_reason=result.done_reason or "unknown",
        trajectory_path=str(trajectory_path) if trajectory_path is not None else None,
        tokens_in=stats.tokens_in,
        tokens_out=stats.tokens_out,
        latency_s=stats.latency_s,
        cost_usd=stats.cost_usd,
        error=error,
    )


def run_eval(
    tasks: Sequence[TaskSpec],
    policy_factory: PolicyFactory,
    n_samples: int,
    max_workers: int,
    *,
    runner_factory: RunnerFactory,
    out_dir: Path,
    max_cost_usd: float | None = None,
    verbose_trajectory: bool = False,
) -> EvalReport:
    """Run policy evaluation episodes in parallel with bounded workers."""
    out_dir.mkdir(parents=True, exist_ok=True)
    jobs = [
        (task, sample)
        for task in sorted(tasks, key=lambda item: item.id)
        for sample in range(n_samples)
    ]
    results: list[EpisodeResult] = []
    stopped_by_max_cost = False
    next_job = 0
    total_cost = 0.0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {}
        while next_job < len(jobs) or futures:
            while next_job < len(jobs) and len(futures) < max_workers:
                if max_cost_usd is not None and total_cost >= max_cost_usd:
                    stopped_by_max_cost = True
                    break
                task, _sample = jobs[next_job]
                seed = next_job
                trajectory = out_dir / f"{task.id}-{seed}.jsonl"
                future = executor.submit(
                    run_episode,
                    task,
                    policy_factory(seed),
                    runner_factory(),
                    seed,
                    trajectory_path=trajectory,
                    verbose_trajectory=verbose_trajectory,
                )
                futures[future] = (task, seed, trajectory)
                next_job += 1
            if not futures:
                break
            done, _pending = wait(futures, return_when=FIRST_COMPLETED)
            for future in done:
                task, seed, trajectory = futures.pop(future)
                try:
                    result = future.result()
                except Exception as exc:
                    result = EpisodeResult(
                        task_id=task.id,
                        policy_name=policy_factory(seed).name,
                        seed=seed,
                        reward=0.0,
                        steps=0,
                        done_reason="error",
                        trajectory_path=str(trajectory),
                        error=str(exc),
                    )
                results.append(result)
                total_cost += result.cost_usd
        for future in futures:
            future.cancel()

    policy_name = results[0].policy_name if results else policy_factory(0).name
    report = aggregate_results(
        policy_name=policy_name,
        n_samples=n_samples,
        max_workers=max_workers,
        results=sorted(results, key=lambda item: (item.task_id, item.seed)),
        stopped_by_max_cost=stopped_by_max_cost,
    )
    (out_dir / "report.json").write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return report


def read_report(path: Path | str) -> EvalReport:
    """Read a saved EvalReport from a run directory or report file."""
    report_path = Path(path)
    if report_path.is_dir():
        report_path = report_path / "report.json"
    return EvalReport.model_validate_json(report_path.read_text(encoding="utf-8"))


def report_table(report: EvalReport) -> str:
    """Render a readable plain-text report table."""
    lines = [
        "TASK\tSEED\tREWARD\tSTEPS\tDONE\tCOST\tERROR",
        *[
            (
                f"{result.task_id}\t{result.seed}\t{result.reward:.3f}\t"
                f"{result.steps}\t{result.done_reason}\t${result.cost_usd:.6f}\t"
                f"{result.error or ''}"
            )
            for result in report.results
        ],
        "",
        (
            f"mean_reward={report.mean_reward:.3f} mean_steps={report.mean_steps:.2f} "
            f"total_cost=${report.total_cost_usd:.6f} "
            f"done_reasons={json.dumps(report.done_reasons)}"
        ),
    ]
    if report.stopped_by_max_cost:
        lines.append("stopped_by_max_cost=true")
    return "\n".join(lines)
