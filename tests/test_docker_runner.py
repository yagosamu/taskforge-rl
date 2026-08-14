"""Tests for Docker runner availability behavior."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from taskforge.runners import DockerRunner

DOCKER_AVAILABLE = shutil.which("docker") is not None
if DOCKER_AVAILABLE:
    DOCKER_AVAILABLE = subprocess.run(
        ["docker", "version"],
        capture_output=True,
        text=True,
        check=False,
        timeout=5,
    ).returncode == 0


@pytest.mark.skipif(not DOCKER_AVAILABLE, reason="Docker CLI/daemon is unavailable")
def test_docker_runner_executes_command() -> None:
    """DockerRunner can execute a simple Python command when Docker is available."""
    runner = DockerRunner()
    result = runner.exec(["python", "-c", "print('ok')"], cwd=Path.cwd(), timeout_s=10)

    assert result.returncode == 0
    assert "ok" in result.stdout
