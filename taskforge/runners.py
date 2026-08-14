"""Command runners for TaskForge environments."""

from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Protocol

from taskforge.models import RunResult


class Runner(Protocol):
    """Protocol for executing commands inside a workspace."""

    def exec(self, cmd: list[str], cwd: Path, timeout_s: int) -> RunResult:
        """Execute a command without a shell and return captured output."""
        ...


class SubprocessRunner:
    """Runner backed by Python subprocesses."""

    def exec(self, cmd: list[str], cwd: Path, timeout_s: int) -> RunResult:
        """Execute a command with captured output and a hard timeout."""
        started = time.monotonic()
        process = subprocess.Popen(
            cmd,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            shell=False,
            start_new_session=os.name != "nt",
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
        )
        try:
            stdout, stderr = process.communicate(timeout=timeout_s)
            timed_out = False
        except subprocess.TimeoutExpired:
            timed_out = True
            _kill_process_group(process)
            stdout, stderr = process.communicate()
        return RunResult(
            cmd=cmd,
            cwd=cwd,
            returncode=process.returncode,
            stdout=stdout,
            stderr=stderr,
            timed_out=timed_out,
            duration_s=time.monotonic() - started,
        )


class DockerUnavailableError(RuntimeError):
    """Raised when Docker CLI is not available for DockerRunner."""


class DockerRunner:
    """Runner that executes commands inside a locked-down Docker container."""

    def __init__(self, *, image: str = "python:3.11-slim") -> None:
        """Create a Docker runner using a Python image."""
        if shutil.which("docker") is None:
            raise DockerUnavailableError(
                "Docker CLI is unavailable; use --runner subprocess instead."
            )
        self.image = image

    def exec(self, cmd: list[str], cwd: Path, timeout_s: int) -> RunResult:
        """Execute a command in Docker with no network and constrained resources."""
        started = time.monotonic()
        mount = cwd.resolve()
        container_cmd = (
            ["python", *cmd[1:]]
            if cmd and Path(cmd[0]) == Path(sys.executable)
            else cmd
        )
        docker_cmd = [
            "docker",
            "run",
            "--rm",
            "--read-only",
            "--tmpfs",
            "/tmp",
            "--env",
            "PYTHONDONTWRITEBYTECODE=1",
            "--network",
            "none",
            "--memory",
            "512m",
            "--cpus",
            "1",
            "--user",
            "65532:65532",
            "--mount",
            f"type=bind,source={mount},target=/workspace",
            "--workdir",
            "/workspace",
            self.image,
            *container_cmd,
        ]
        process = subprocess.Popen(
            docker_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            shell=False,
            start_new_session=os.name != "nt",
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
        )
        try:
            stdout, stderr = process.communicate(timeout=timeout_s)
            timed_out = False
        except subprocess.TimeoutExpired:
            timed_out = True
            _kill_process_group(process)
            stdout, stderr = process.communicate()
        return RunResult(
            cmd=cmd,
            cwd=cwd,
            returncode=process.returncode,
            stdout=stdout,
            stderr=stderr,
            timed_out=timed_out,
            duration_s=time.monotonic() - started,
        )


def _kill_process_group(process: subprocess.Popen[str]) -> None:
    if os.name == "nt":
        process.kill()
        return
    os.killpg(process.pid, signal.SIGKILL)
