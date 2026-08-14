"""Tests for workspace path safety."""

from __future__ import annotations

from pathlib import Path

import pytest

from taskforge.actions import WriteFile
from taskforge.env import TaskEnv
from taskforge.loader import load_task
from taskforge.paths import PathEscapeError, resolve_in_workspace


def test_parent_escape_raises(tmp_path: Path) -> None:
    """Parent directory traversal cannot leave the workspace."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    with pytest.raises(PathEscapeError):
        resolve_in_workspace(workspace, "../../etc/passwd")


def test_absolute_escape_raises(tmp_path: Path) -> None:
    """Absolute paths outside the workspace are rejected."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    with pytest.raises(PathEscapeError):
        resolve_in_workspace(workspace, tmp_path / "outside.txt")


def test_symlink_escape_raises(tmp_path: Path) -> None:
    """Symlinks resolving outside the workspace are rejected."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("secret", encoding="utf-8")
    try:
        (workspace / "link.txt").symlink_to(outside)
    except OSError as exc:
        pytest.skip(f"symlink creation unavailable: {exc}")

    with pytest.raises(PathEscapeError):
        resolve_in_workspace(workspace, "link.txt")


def test_write_file_escape_paths_end_episode_without_writing(tmp_path: Path) -> None:
    """WriteFile escape attempts are rejected by the environment."""
    task = load_task(Path("tasks/fix-retry-backoff"))
    outside = tmp_path / "outside.txt"

    for bad_path in ["../../etc/passwd", str(outside)]:
        with TaskEnv(task) as env:
            env.reset()
            result = env.step(WriteFile(path=bad_path, content="owned"))

        assert result.done is True
        assert result.done_reason == "error"
        assert result.reward == 0.0
    assert not outside.exists()
