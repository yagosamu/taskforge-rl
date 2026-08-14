"""Environment API for running TaskForge tasks."""

from __future__ import annotations

import time
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from taskforge.actions import Action, Finish, ListFiles, ReadFile, RunTests, WriteFile
from taskforge.events import EventLogger
from taskforge.grading import grade, run_pytest
from taskforge.models import TaskSpec
from taskforge.paths import PathEscapeError, resolve_in_workspace
from taskforge.runners import Runner, SubprocessRunner
from taskforge.trajectory import TrajectoryWriter
from taskforge.truncation import truncate
from taskforge.workspace import ephemeral_workspace


class Observation(BaseModel):
    """Environment observation returned after reset and step."""

    model_config = ConfigDict(extra="forbid")

    task_id: str
    workspace: Path
    step: int
    remaining_steps: int
    last_output: str = ""
    truncated: bool = False


class StepResult(BaseModel):
    """Result of one environment step."""

    model_config = ConfigDict(extra="forbid")

    observation: Observation
    reward: float
    done: bool
    done_reason: str | None = None
    info: dict[str, object] = Field(default_factory=dict)


class TaskEnv:
    """Single-task RL-style environment."""

    def __init__(
        self,
        task: TaskSpec,
        *,
        runner: Runner | None = None,
        event_log_path: Path | None = None,
        trajectory_path: Path | None = None,
        verbose_trajectory: bool = False,
        trajectory_metadata: dict[str, object] | None = None,
        max_steps: int | None = None,
    ) -> None:
        """Create an environment for one task."""
        self.task = task
        self.runner = runner or SubprocessRunner()
        self.event_log_path = event_log_path
        self.trajectory_path = trajectory_path
        self.verbose_trajectory = verbose_trajectory
        self.trajectory_metadata = trajectory_metadata or {}
        self.max_steps_override = max_steps
        self._workspace_cm: object | None = None
        self._logger_cm: object | None = None
        self._logger: EventLogger | None = None
        self._trajectory: TrajectoryWriter | None = None
        self.workspace: Path | None = None
        self.step_count = 0
        self.done = False
        self.done_reason: str | None = None
        self._started_at = 0.0

    def reset(self) -> Observation:
        """Start a new episode and return the first observation."""
        self.close()
        self._workspace_cm = ephemeral_workspace(self.task)
        self.workspace = self._workspace_cm.__enter__()  # type: ignore[attr-defined]
        self.step_count = 0
        self.done = False
        self.done_reason = None
        self._started_at = time.monotonic()
        if self.event_log_path is not None:
            self._logger_cm = EventLogger(self.event_log_path, task_id=self.task.id)
            self._logger = self._logger_cm.__enter__()  # type: ignore[attr-defined]
        if self.trajectory_path is not None:
            self._trajectory = TrajectoryWriter(
                self.trajectory_path,
                task_id=self.task.id,
                verbose_observations=self.verbose_trajectory,
                metadata=self.trajectory_metadata,
            )
        obs = self._observation()
        self._emit("reset", {"workspace": str(self.workspace)})
        if self._trajectory is not None:
            self._trajectory.write_start(step=self.step_count, observation=obs)
        return obs

    def step(self, action: Action) -> StepResult:
        """Apply an action, decrement the step budget, and return the result."""
        if self.workspace is None or self.done:
            raise RuntimeError(
                "reset() must be called before step(), and done episodes cannot step"
            )

        self.step_count += 1
        self._emit("step", {"action": action.model_dump()})
        reward = 0.0
        info: dict[str, object] = {}
        last_output = ""

        try:
            if isinstance(action, ReadFile):
                target = resolve_in_workspace(self.workspace, action.path)
                last_output = target.read_text(encoding="utf-8")
                info["path"] = str(target.relative_to(self.workspace.resolve()))
            elif isinstance(action, WriteFile):
                target = resolve_in_workspace(self.workspace, action.path)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(action.content, encoding="utf-8")
                last_output = f"wrote {len(action.content)} chars to {action.path}"
            elif isinstance(action, ListFiles):
                target = resolve_in_workspace(self.workspace, action.path)
                root = self.workspace.resolve()
                files = sorted(
                    str(path.relative_to(root))
                    for path in target.rglob("*")
                    if path.is_file()
                )
                last_output = "\n".join(files)
                info["files"] = files
            elif isinstance(action, RunTests):
                report = run_pytest(
                    self.runner,
                    self.workspace,
                    [Path(test) for test in self.task.tests.visible],
                    timeout_s=self.task.budget.test_timeout_s,
                )
                last_output = report.stdout + report.stderr
                info["visible_tests"] = report.model_dump(mode="json")
                if report.timed_out:
                    self._finish("timeout")
            elif isinstance(action, Finish):
                self._finish("finish")
        except (OSError, UnicodeError, PathEscapeError) as exc:
            last_output = str(exc)
            info["error"] = str(exc)
            self._finish("error")

        if self.step_count >= self._max_steps():
            self._finish("step_limit")
        if time.monotonic() - self._started_at >= self.task.budget.episode_timeout_s:
            self._finish("timeout")

        if self.done:
            breakdown = grade(self.task, self.workspace, self.runner)
            reward = breakdown.reward
            info["reward_breakdown"] = breakdown.model_dump(mode="json")

        obs = self._observation(last_output=last_output)
        result = StepResult(
            observation=obs,
            reward=reward,
            done=self.done,
            done_reason=self.done_reason,
            info=info,
        )
        if self._trajectory is not None:
            self._trajectory.write_step(
                step=self.step_count,
                action=action.model_dump(mode="json"),
                reward=reward,
                done=self.done,
                done_reason=self.done_reason,
                observation=obs,
            )
        if self.done:
            self._emit("reward", {"reward": reward, "info": info})
            if self._trajectory is not None:
                self._trajectory.write_end(
                    step=self.step_count,
                    terminal_reward=reward,
                    done_reason=self.done_reason or "unknown",
                )
        return result

    def close(self) -> None:
        """Clean up any active episode resources."""
        if self._logger_cm is not None:
            self._logger_cm.__exit__(None, None, None)  # type: ignore[attr-defined]
        self._logger_cm = None
        self._logger = None
        if self._workspace_cm is not None:
            self._workspace_cm.__exit__(None, None, None)  # type: ignore[attr-defined]
        self._workspace_cm = None
        self.workspace = None
        self._trajectory = None

    def abort(self, reason: str = "error", message: str = "") -> StepResult:
        """End an active episode after an unrecoverable external error."""
        if self.workspace is None or self.done:
            raise RuntimeError(
                "reset() must be called before abort(), and done episodes cannot abort"
            )
        self._finish(reason)
        breakdown = grade(self.task, self.workspace, self.runner)
        obs = self._observation(last_output=message)
        result = StepResult(
            observation=obs,
            reward=breakdown.reward,
            done=True,
            done_reason=self.done_reason,
            info={"error": message, "reward_breakdown": breakdown.model_dump(mode="json")},
        )
        if self._trajectory is not None:
            self._trajectory.write_step(
                step=self.step_count,
                action={"type": "abort", "reason": reason},
                reward=result.reward,
                done=True,
                done_reason=self.done_reason,
                observation=obs,
            )
            self._trajectory.write_end(
                step=self.step_count,
                terminal_reward=result.reward,
                done_reason=self.done_reason or reason,
            )
        self._emit("reward", {"reward": result.reward, "info": result.info})
        return result

    def _observation(self, *, last_output: str = "") -> Observation:
        assert self.workspace is not None
        max_chars = self.task.limits.max_observation_chars
        task_id, truncated_task = truncate(self.task.id, max_chars)
        workspace, truncated_workspace = truncate(str(self.workspace), max_chars)
        output, truncated_output = truncate(last_output, max_chars)
        return Observation(
            task_id=task_id,
            workspace=Path(workspace),
            step=self.step_count,
            remaining_steps=max(self._max_steps() - self.step_count, 0),
            last_output=output,
            truncated=truncated_task or truncated_workspace or truncated_output,
        )

    def _max_steps(self) -> int:
        if self.max_steps_override is not None:
            return self.max_steps_override
        return self.task.limits.max_steps

    def _finish(self, done_reason: str) -> None:
        if not self.done:
            self.done = True
            self.done_reason = done_reason

    def _emit(self, event_type: str, payload: dict[str, object]) -> None:
        if self._logger is not None:
            self._logger.emit(step=self.step_count, event_type=event_type, payload=payload)

    def __enter__(self) -> TaskEnv:
        """Return this environment for context manager use."""
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        """Clean up resources when leaving a context manager."""
        self.close()
