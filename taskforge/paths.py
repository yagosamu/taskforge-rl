"""Workspace path safety helpers."""

from __future__ import annotations

from pathlib import Path


class PathEscapeError(ValueError):
    """Raised when a requested path resolves outside the workspace."""


def resolve_in_workspace(workspace: Path, path: str | Path) -> Path:
    """Resolve a path under a workspace and reject escapes via absolute paths or symlinks."""
    root = workspace.resolve()
    requested = Path(path)
    candidate = requested if requested.is_absolute() else root / requested
    resolved = _resolve_existing_or_parent(candidate)
    if resolved != root and root not in resolved.parents:
        raise PathEscapeError(f"path escapes workspace: {path}")
    return resolved


def _resolve_existing_or_parent(path: Path) -> Path:
    if path.exists():
        return path.resolve()
    parent = path.parent.resolve()
    return parent / path.name
