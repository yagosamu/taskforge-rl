"""Hidden tests."""

from app import hidden_value


def test_hidden() -> None:
    """Hidden value must be fixed."""
    assert hidden_value() == 2
