"""Hidden tests."""

from app import answer


def test_hidden() -> None:
    """Hidden behavior requires the fix."""
    assert answer() == 42
