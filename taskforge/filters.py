"""Task filtering helpers used by CLI commands."""

from __future__ import annotations

from collections.abc import Sequence

from taskforge.models import TaskSpec


def filter_tasks(
    tasks: Sequence[TaskSpec],
    *,
    tier: int | None = None,
    tags: Sequence[str] | None = None,
) -> list[TaskSpec]:
    """Filter tasks by optional metadata tier and required tags."""
    required_tags = set(tags or [])
    filtered: list[TaskSpec] = []
    for task in tasks:
        if tier is not None and task.metadata.tier != tier:
            continue
        if required_tags and not required_tags.issubset(set(task.metadata.tags)):
            continue
        filtered.append(task)
    return filtered
