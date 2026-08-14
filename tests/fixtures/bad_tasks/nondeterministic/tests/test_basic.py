"""Visible tests."""

from app import answer


def test_visible() -> None:
    """Visible behavior passes."""
    assert answer() == 42
