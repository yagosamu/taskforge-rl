"""Task discovery, parsing, and validation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from taskforge.grading import REWARD_REGISTRY
from taskforge.models import TaskSpec, TaskValidationError


def load_task(path: Path | str) -> TaskSpec:
    """Load and validate a task from a task directory or task.yaml file."""
    candidate = Path(path)
    task_file = candidate / "task.yaml" if candidate.is_dir() else candidate
    try:
        raw = yaml.safe_load(task_file.read_text(encoding="utf-8"))
    except OSError as exc:
        raise TaskValidationError(task_file, f"could not read task file: {exc}") from exc
    if not isinstance(raw, dict):
        raise TaskValidationError(task_file, "task.yaml must contain a mapping")

    data: dict[str, Any] = dict(raw)
    data["root"] = task_file.parent
    try:
        task = TaskSpec.model_validate(data)
    except ValidationError as exc:
        raise TaskValidationError(task_file, str(exc)) from exc

    _validate_references(task_file, task)
    return task


def discover_tasks(directory: Path | str) -> list[TaskSpec]:
    """Discover and validate every task.yaml under a directory."""
    root = Path(directory)
    task_files = sorted(root.glob("*/task.yaml"))
    return [load_task(task_file) for task_file in task_files]


def _validate_references(task_file: Path, task: TaskSpec) -> None:
    if task.reward.type not in REWARD_REGISTRY:
        raise TaskValidationError(task_file, f"unknown reward type: {task.reward.type}")
    if not task.workspace_path.is_dir():
        raise TaskValidationError(task_file, f"workspace directory not found: {task.workspace}")
    for test_path in task.all_test_paths:
        if not test_path.is_file():
            raise TaskValidationError(task_file, f"referenced test file not found: {test_path}")
