"""Pydantic models for TaskForge task specifications."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class TaskValidationError(ValueError):
    """Raised when a task specification or its referenced files are invalid."""

    def __init__(self, path: Path, message: str) -> None:
        """Create a validation error tied to the offending file path."""
        self.path = path
        super().__init__(f"{path}: {message}")


class TestSpec(BaseModel):
    """Lists visible and hidden tests for a task."""

    model_config = ConfigDict(extra="forbid")

    visible: list[str] = Field(default_factory=list)
    hidden: list[str] = Field(default_factory=list)


class RewardSpec(BaseModel):
    """Reward configuration for a task."""

    model_config = ConfigDict(extra="forbid")

    type: str
    partial_credit: bool = True


class BudgetSpec(BaseModel):
    """Episode limits for a task."""

    model_config = ConfigDict(extra="forbid")

    max_steps: int = Field(default=5, ge=1)
    step_timeout_s: int = Field(default=10, ge=1)
    test_timeout_s: int = Field(default=20, ge=1)
    episode_timeout_s: int = Field(default=300, ge=1)


class LimitsSpec(BaseModel):
    """Observation and output limits for a task."""

    model_config = ConfigDict(extra="forbid")

    max_observation_chars: int = Field(default=4000, ge=1)
    max_steps: int = Field(default=25, ge=1)


class TaskSpec(BaseModel):
    """A complete, validated task definition."""

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    id: str
    title: str
    description: str = ""
    root: Path
    workspace: str = "workspace"
    tests: TestSpec
    reward: RewardSpec
    budget: BudgetSpec = Field(default_factory=BudgetSpec)
    limits: LimitsSpec = Field(default_factory=LimitsSpec)

    @property
    def workspace_path(self) -> Path:
        """Return the source workspace directory for this task."""
        return self.root / self.workspace

    @property
    def visible_test_paths(self) -> list[Path]:
        """Return visible test paths rooted at the task directory."""
        return [self.root / test_file for test_file in self.tests.visible]

    @property
    def hidden_test_paths(self) -> list[Path]:
        """Return hidden test paths rooted at the task directory."""
        return [self.root / test_file for test_file in self.tests.hidden]

    @property
    def all_test_paths(self) -> list[Path]:
        """Return all referenced test paths rooted at the task directory."""
        return self.visible_test_paths + self.hidden_test_paths

    @property
    def max_steps(self) -> int:
        """Return the task's canonical episode step budget."""
        return self.limits.max_steps

    @model_validator(mode="after")
    def _ensure_test_sets_do_not_overlap(self) -> TaskSpec:
        """Ensure visible and hidden test lists do not overlap."""
        visible = set(self.tests.visible)
        hidden = set(self.tests.hidden)
        overlap = visible & hidden
        if overlap:
            joined = ", ".join(sorted(overlap))
            raise ValueError(f"visible and hidden tests overlap: {joined}")
        return self


class RunResult(BaseModel):
    """Result of a command executed by a runner."""

    model_config = ConfigDict(extra="forbid")

    cmd: list[str]
    cwd: Path
    returncode: int | None
    stdout: str
    stderr: str
    timed_out: bool = False
    duration_s: float


class TestReport(BaseModel):
    """Parsed pytest results."""

    model_config = ConfigDict(extra="forbid")

    total: int
    passed: int
    failed: int
    errors: int
    skipped: int
    returncode: int | None
    stdout: str
    stderr: str
    timed_out: bool = False


class RewardBreakdown(BaseModel):
    """Reward value with human-readable scoring details."""

    model_config = ConfigDict(extra="forbid")

    reward: float
    components: dict[str, float]
    reason: str
    report: TestReport | None = None


class ActionBase(BaseModel):
    """Base class for serializable environment actions."""

    model_config = ConfigDict(extra="forbid")

    type: str


class RunTestsAction(ActionBase):
    """Action requesting visible test execution."""

    type: Literal["run_tests"] = "run_tests"


class FinishAction(ActionBase):
    """Action requesting terminal grading."""

    type: Literal["finish"] = "finish"
