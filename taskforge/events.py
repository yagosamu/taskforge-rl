"""JSONL event logging for TaskForge runs."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TextIO
from uuid import uuid4


class EventLogger:
    """Write one JSON object per event to a JSONL file."""

    def __init__(self, path: Path, *, run_id: str | None = None, task_id: str = "") -> None:
        """Create an event logger for a task run."""
        self.path = path
        self.run_id = run_id or str(uuid4())
        self.task_id = task_id
        self._file: TextIO | None = None

    def __enter__(self) -> EventLogger:
        """Open the JSONL file for writing."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._file = self.path.open("a", encoding="utf-8")
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        """Close the JSONL file."""
        if self._file is not None:
            self._file.close()

    def emit(self, *, step: int, event_type: str, payload: dict[str, Any]) -> None:
        """Write one event and flush it immediately."""
        if self._file is None:
            raise RuntimeError("EventLogger must be opened before emitting events")
        event = {
            "run_id": self.run_id,
            "task_id": self.task_id,
            "step": step,
            "event_type": event_type,
            "payload": payload,
            "ts": datetime.now(UTC).isoformat(),
        }
        self._file.write(json.dumps(event, sort_keys=True) + "\n")
        self._file.flush()
