"""Data migration helpers."""

from __future__ import annotations

from datetime import date


def rows_to_archive(rows: list[dict[str, object]], cutoff: date) -> list[int]:
    """Return ids for rows with created_at at or before cutoff."""
    return [
        int(row["id"])
        for row in rows
        if row.get("created_at") is not None and row["created_at"] <= cutoff
    ]
