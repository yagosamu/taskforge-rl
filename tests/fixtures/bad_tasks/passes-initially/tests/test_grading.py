"""Hidden tests."""

from app import answer


def test_answer_hidden() -> None:
    """The hidden answer is also correct."""
    assert answer() == 42
