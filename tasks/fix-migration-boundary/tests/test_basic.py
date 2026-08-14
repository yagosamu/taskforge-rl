"""Visible migration tests."""

from datetime import date

from migration import rows_to_archive


def test_older_rows_archive() -> None:
    """Rows before the cutoff are archived."""
    rows = [{"id": 1, "created_at": date(2024, 1, 1)}]
    assert rows_to_archive(rows, date(2024, 2, 1)) == [1]
