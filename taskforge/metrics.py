"""Evaluation metrics for TaskForge."""

from __future__ import annotations

from collections import Counter
from math import comb

from pydantic import BaseModel, ConfigDict, Field


class EpisodeResult(BaseModel):
    """Result from one evaluated episode."""

    model_config = ConfigDict(extra="forbid")

    task_id: str
    policy_name: str
    seed: int
    reward: float
    steps: int
    done_reason: str
    trajectory_path: str | None = None
    tokens_in: int = 0
    tokens_out: int = 0
    latency_s: float = 0.0
    cost_usd: float = 0.0
    invalid_actions: int = 0
    error: str | None = None


class EvalReport(BaseModel):
    """Aggregated evaluation report."""

    model_config = ConfigDict(extra="forbid")

    policy_name: str
    n_samples: int
    max_workers: int
    results: list[EpisodeResult]
    mean_reward: float
    mean_steps: float
    mean_cost_usd: float
    total_cost_usd: float
    done_reasons: dict[str, int] = Field(default_factory=dict)
    stopped_by_max_cost: bool = False


def pass_at_k(n: int, c: int, k: int) -> float:
    """Compute the standard unbiased pass@k estimator."""
    if n <= 0 or c <= 0 or k <= 0:
        return 0.0
    if c >= n:
        return 1.0
    if k >= n:
        return 1.0
    return 1.0 - comb(n - c, k) / comb(n, k)


def aggregate_results(
    *,
    policy_name: str,
    n_samples: int,
    max_workers: int,
    results: list[EpisodeResult],
    stopped_by_max_cost: bool = False,
) -> EvalReport:
    """Aggregate episode results into an evaluation report."""
    rewards = [result.reward for result in results]
    steps = [result.steps for result in results]
    costs = [result.cost_usd for result in results]
    return EvalReport(
        policy_name=policy_name,
        n_samples=n_samples,
        max_workers=max_workers,
        results=results,
        mean_reward=sum(rewards) / len(rewards) if rewards else 0.0,
        mean_steps=sum(steps) / len(steps) if steps else 0.0,
        mean_cost_usd=sum(costs) / len(costs) if costs else 0.0,
        total_cost_usd=sum(costs),
        done_reasons=dict(Counter(result.done_reason for result in results)),
        stopped_by_max_cost=stopped_by_max_cost,
    )
