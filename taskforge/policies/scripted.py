"""Scripted baseline policy."""

from __future__ import annotations

from taskforge.actions import Action, Finish, RunTests
from taskforge.env import Observation
from taskforge.policies.base import PolicyStats


class ScriptedPolicy:
    """Run visible tests once, then finish."""

    name = "scripted"

    def __init__(self) -> None:
        """Create a scripted policy."""
        self._step = 0

    def reset(self) -> None:
        """Reset the policy step counter."""
        self._step = 0

    def act(self, obs: Observation) -> Action:
        """Return RunTests on the first step and Finish afterward."""
        del obs
        self._step += 1
        if self._step == 1:
            return RunTests()
        return Finish()

    def stats(self) -> PolicyStats:
        """Return zero-cost policy stats."""
        return PolicyStats()
