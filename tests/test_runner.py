"""Tests for subprocess runner behavior."""

from __future__ import annotations

import sys
from pathlib import Path

from taskforge.runners import SubprocessRunner


def test_subprocess_runner_enforces_timeout(tmp_path: Path) -> None:
    """Long-running commands time out and are killed."""
    runner = SubprocessRunner()
    result = runner.exec(
        [sys.executable, "-c", "import time; time.sleep(10)"],
        cwd=tmp_path,
        timeout_s=1,
    )

    assert result.timed_out is True
    assert result.returncode is not None
