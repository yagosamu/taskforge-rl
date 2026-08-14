"""Hidden tests."""

from app import answer


def test_hidden() -> None:
    """The answer must be correct."""
    assert answer() == 42
