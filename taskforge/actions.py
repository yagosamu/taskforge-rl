"""Serializable action space for TaskForge agents."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError, model_validator


class ActionValidationError(ValueError):
    """Raised when an action payload cannot be parsed safely."""


class ReadFile(BaseModel):
    """Read a UTF-8 text file from the workspace."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["read_file"] = "read_file"
    path: str


class WriteFile(BaseModel):
    """Write UTF-8 text to a file in the workspace."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["write_file"] = "write_file"
    path: str
    content: str


class ListFiles(BaseModel):
    """List files under a workspace directory."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["list_files"] = "list_files"
    path: str = "."


class RunTests(BaseModel):
    """Run visible tests for the task."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["run_tests"] = "run_tests"
    scope: Literal["visible", "hidden"] = "visible"

    @model_validator(mode="after")
    def _reject_hidden_scope(self) -> RunTests:
        """Reject direct execution of hidden grading tests."""
        if self.scope == "hidden":
            raise ValueError('RunTests(scope="hidden") is not allowed')
        return self


class Finish(BaseModel):
    """Ask the environment to grade and end the episode."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["finish"] = "finish"


Action = Annotated[
    ReadFile | WriteFile | ListFiles | RunTests | Finish,
    Field(discriminator="type"),
]
_ACTION_ADAPTER: TypeAdapter[Action] = TypeAdapter(Action)
ACTION_TYPES = {"read_file", "write_file", "list_files", "run_tests", "finish"}


def parse_action(data: dict[str, object]) -> Action:
    """Parse an action dictionary and raise a clear error for invalid action payloads."""
    action_type = data.get("type")
    if action_type not in ACTION_TYPES:
        raise ActionValidationError(f"unknown action type: {action_type!r}")
    try:
        return _ACTION_ADAPTER.validate_python(data)
    except ValidationError as exc:
        raise ActionValidationError(str(exc)) from exc
