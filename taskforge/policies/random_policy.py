"""Seeded random baseline policy."""

from __future__ import annotations

import random

from taskforge.actions import Action, Finish, ListFiles, ReadFile, RunTests, WriteFile
from taskforge.env import Observation
from taskforge.policies.base import PolicyStats


class RandomPolicy:
    """Sample valid actions using a seeded RNG."""

    name = "random"

    def __init__(self, *, seed: int | None = None) -> None:
        """Create a random policy."""
        self._seed = seed
        self._rng = random.Random(seed)

    def reset(self) -> None:
        """Reset the RNG to its original seed."""
        self._rng = random.Random(self._seed)

    def act(self, obs: Observation) -> Action:
        """Sample a valid non-hidden action."""
        choices = ["list", "read", "write", "tests", "finish"]
        choice = self._rng.choice(choices)
        if choice == "list":
            return ListFiles(path=".")
        if choice == "read":
            return ReadFile(path="client.py")
        if choice == "write":
            return WriteFile(path=f"random_note_{obs.step}.txt", content="random baseline\n")
        if choice == "tests":
            return RunTests()
        return Finish()

    def stats(self) -> PolicyStats:
        """Return zero-cost policy stats."""
        return PolicyStats()
