"""Visible tests."""

from app import answer


def test_answer() -> None:
    """The answer is correct."""
    assert answer() == 42
