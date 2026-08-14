"""Tests for task loading and validation."""

from __future__ import annotations

from pathlib import Path

import pytest

from taskforge.loader import load_task
from taskforge.models import TaskValidationError


def test_loader_rejects_missing_test_file(tmp_path: Path) -> None:
    """A task referencing a missing test file fails validation clearly."""
    task_dir = tmp_path / "broken"
    (task_dir / "workspace").mkdir(parents=True)
    (task_dir / "task.yaml").write_text(
        """
id: broken
title: Broken
workspace: workspace
tests:
  visible:
    - tests/missing.py
  hidden: []
reward:
  type: test_pass_ratio
""",
        encoding="utf-8",
    )

    with pytest.raises(TaskValidationError) as exc_info:
        load_task(task_dir)

    assert str(task_dir / "task.yaml") in str(exc_info.value)
    assert "referenced test file not found" in str(exc_info.value)
