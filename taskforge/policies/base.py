"""Policy protocol for agents that drive TaskForge environments."""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, ConfigDict

from taskforge.actions import Action
from taskforge.env import Observation


class PolicyStats(BaseModel):
    """Usage and cost statistics accumulated by a policy."""

    model_config = ConfigDict(extra="forbid")

    tokens_in: int = 0
    tokens_out: int = 0
    latency_s: float = 0.0
    cost_usd: float = 0.0


class Policy(Protocol):
    """Protocol implemented by all TaskForge policies."""

    name: str

    def reset(self) -> None:
        """Reset any per-episode policy state."""
        ...

    def act(self, obs: Observation) -> Action:
        """Choose the next action from an observation."""
        ...

    def stats(self) -> PolicyStats:
        """Return policy usage and cost statistics."""
        ...
