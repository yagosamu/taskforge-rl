"""Visible tests."""

from app import answer


def test_visible() -> None:
    """Visible behavior is weak."""
    assert isinstance(answer(), int)
