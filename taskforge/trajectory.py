"""Versioned trajectory JSONL writer and reader."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, TypeAdapter

SCHEMA_VERSION = "1.0"


class TrajectoryObservation(BaseModel):
    """Observation reference stored in a trajectory record."""

    model_config = ConfigDict(extra="forbid")

    digest: str
    side_file: str | None = None
    truncated: bool


class EpisodeStartRecord(BaseModel):
    """Trajectory record written when an episode starts."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"] = SCHEMA_VERSION
    record_type: Literal["episode_start"] = "episode_start"
    run_id: str
    task_id: str
    step: int
    observation: TrajectoryObservation
    metadata: dict[str, Any] = {}
    ts: str


class StepRecord(BaseModel):
    """Trajectory record written after an action is applied."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"] = SCHEMA_VERSION
    record_type: Literal["step"] = "step"
    run_id: str
    task_id: str
    step: int
    action: dict[str, Any]
    reward: float
    done: bool
    done_reason: str | None
    observation: TrajectoryObservation
    ts: str


class EpisodeEndRecord(BaseModel):
    """Trajectory record written when an episode ends."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"] = SCHEMA_VERSION
    record_type: Literal["episode_end"] = "episode_end"
    run_id: str
    task_id: str
    step: int
    terminal_reward: float
    done_reason: str
    ts: str


TrajectoryRecord = EpisodeStartRecord | StepRecord | EpisodeEndRecord
_RECORD_ADAPTER = TypeAdapter(
    EpisodeStartRecord | StepRecord | EpisodeEndRecord
)


class Episode(BaseModel):
    """A parsed trajectory episode."""

    model_config = ConfigDict(extra="forbid")

    records: list[TrajectoryRecord]

    @property
    def actions(self) -> list[dict[str, Any]]:
        """Return recorded action payloads in order."""
        return [record.action for record in self.records if isinstance(record, StepRecord)]

    @property
    def terminal_reward(self) -> float:
        """Return the terminal reward from the final episode record."""
        for record in reversed(self.records):
            if isinstance(record, EpisodeEndRecord):
                return record.terminal_reward
        raise ValueError("trajectory has no episode_end record")


class TrajectoryWriter:
    """Write versioned trajectory records to JSONL."""

    def __init__(
        self,
        path: Path,
        *,
        task_id: str,
        run_id: str | None = None,
        verbose_observations: bool = False,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Create a trajectory writer."""
        self.path = path
        self.task_id = task_id
        self.run_id = run_id or str(uuid4())
        self.verbose_observations = verbose_observations
        self.metadata = metadata or {}
        self._side_path = path.with_suffix(path.suffix + ".observations.jsonl")

    def write_start(self, *, step: int, observation: BaseModel) -> None:
        """Write an episode_start record."""
        record = EpisodeStartRecord(
            run_id=self.run_id,
            task_id=self.task_id,
            step=step,
            observation=self._observation_ref(step, observation),
            metadata=self.metadata,
            ts=_now(),
        )
        self._write(record)

    def write_step(
        self,
        *,
        step: int,
        action: dict[str, Any],
        reward: float,
        done: bool,
        done_reason: str | None,
        observation: BaseModel,
    ) -> None:
        """Write a step record."""
        record = StepRecord(
            run_id=self.run_id,
            task_id=self.task_id,
            step=step,
            action=action,
            reward=reward,
            done=done,
            done_reason=done_reason,
            observation=self._observation_ref(step, observation),
            ts=_now(),
        )
        self._write(record)

    def write_end(self, *, step: int, terminal_reward: float, done_reason: str) -> None:
        """Write an episode_end record."""
        record = EpisodeEndRecord(
            run_id=self.run_id,
            task_id=self.task_id,
            step=step,
            terminal_reward=terminal_reward,
            done_reason=done_reason,
            ts=_now(),
        )
        self._write(record)

    def _observation_ref(self, step: int, observation: BaseModel) -> TrajectoryObservation:
        payload = observation.model_dump(mode="json")
        text = json.dumps(payload, sort_keys=True)
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        side_file = None
        if self.verbose_observations:
            side_file = self._side_path.name
            self._side_path.parent.mkdir(parents=True, exist_ok=True)
            with self._side_path.open("a", encoding="utf-8") as handle:
                side_record = {"step": step, "observation": payload}
                handle.write(json.dumps(side_record, sort_keys=True) + "\n")
                handle.flush()
        return TrajectoryObservation(
            digest=digest,
            side_file=side_file,
            truncated=bool(payload.get("truncated", False)),
        )

    def _write(self, record: TrajectoryRecord) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(record.model_dump_json() + "\n")
            handle.flush()


def read_trajectory(path: Path | str) -> Episode:
    """Read a trajectory JSONL file into an Episode model."""
    records: list[TrajectoryRecord] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            records.append(_RECORD_ADAPTER.validate_json(line))
    return Episode(records=records)


def summarize_episode(episode: Episode) -> dict[str, object]:
    """Return aggregate statistics for a parsed episode."""
    end_records = [record for record in episode.records if isinstance(record, EpisodeEndRecord)]
    rewards = [record.terminal_reward for record in end_records]
    steps = [record.step for record in end_records]
    reasons = Counter(record.done_reason for record in end_records)
    return {
        "pass_at_1": (
            sum(1 for reward in rewards if reward >= 1.0) / len(rewards) if rewards else 0.0
        ),
        "mean_reward": sum(rewards) / len(rewards) if rewards else 0.0,
        "mean_steps": sum(steps) / len(steps) if steps else 0.0,
        "done_reasons": dict(reasons),
    }


def _now() -> str:
    return datetime.now(UTC).isoformat()
