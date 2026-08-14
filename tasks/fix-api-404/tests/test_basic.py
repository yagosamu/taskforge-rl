"""Visible API tests."""

from api import get_user


def test_existing_user() -> None:
    """Existing users return 200."""
    assert get_user("ada") == (200, {"name": "Ada"})
