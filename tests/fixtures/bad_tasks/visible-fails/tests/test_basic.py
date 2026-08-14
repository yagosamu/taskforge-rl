"""Visible tests."""

from app import visible_value


def test_visible() -> None:
    """Visible value must stay stable."""
    assert visible_value() == 1
