"""Hidden migration tests."""

from datetime import date

from migration import rows_to_archive


def test_cutoff_day_is_included() -> None:
    """Rows exactly on the cutoff are boundary rows and must archive."""
    rows = [
        {"id": 1, "created_at": date(2024, 1, 31)},
        {"id": 2, "created_at": date(2024, 2, 1)},
        {"id": 3, "created_at": date(2024, 2, 2)},
    ]
    assert rows_to_archive(rows, date(2024, 2, 1)) == [1, 2]
