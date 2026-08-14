"""Ephemeral workspace lifecycle management."""

from __future__ import annotations

import shutil
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from taskforge.models import TaskSpec, TaskValidationError


@contextmanager
def ephemeral_workspace(task: TaskSpec) -> Iterator[Path]:
    """Create a temporary workspace containing source files and tests, then clean it up."""
    with tempfile.TemporaryDirectory(prefix=f"taskforge-{task.id}-") as temp_name:
        destination = Path(temp_name)
        _copy_tree_safe(task.workspace_path, destination)
        restore_tests(task, destination, include_visible=True, include_hidden=True)
        yield destination


def restore_tests(
    task: TaskSpec,
    workspace: Path,
    *,
    include_visible: bool,
    include_hidden: bool,
) -> None:
    """Restore original task test files into an ephemeral workspace."""
    test_files: list[Path] = []
    if include_visible:
        test_files.extend(task.visible_test_paths)
    if include_hidden:
        test_files.extend(task.hidden_test_paths)
    for source in test_files:
        relative = source.relative_to(task.root)
        target = workspace / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.is_symlink():
            raise TaskValidationError(source, "test file must not be a symlink")
        shutil.copy2(source, target, follow_symlinks=False)


def _copy_tree_safe(source: Path, destination: Path) -> None:
    source_root = source.resolve()
    for path in source.rglob("*"):
        if path.is_symlink():
            raise TaskValidationError(path, "workspace symlinks are not supported")
        resolved = path.resolve()
        # Resolve and compare every item so a future platform-specific traversal surprise
        # cannot copy files outside the task's workspace source tree.
        if source_root != resolved and source_root not in resolved.parents:
            raise TaskValidationError(path, "workspace entry resolves outside the workspace")
        relative = path.relative_to(source)
        target = destination / relative
        if path.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        elif path.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target, follow_symlinks=False)
