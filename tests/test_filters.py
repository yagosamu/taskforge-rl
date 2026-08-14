"""Tests for task metadata filters."""

from __future__ import annotations

from pathlib import Path

from taskforge.filters import filter_tasks
from taskforge.loader import discover_tasks


def test_filter_tasks_by_tier_and_tag() -> None:
    """Task filters select the intended benchmark subset."""
    tasks = discover_tasks(Path("tasks"))

    filtered = filter_tasks(tasks, tier=2, tags=["performance"])

    assert [task.id for task in filtered] == ["perf-regression"]
