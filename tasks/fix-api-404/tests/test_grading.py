"""Hidden API tests."""

from api import get_user


def test_missing_user_returns_404() -> None:
    """Missing users return 404 rather than an empty 200."""
    assert get_user("grace") == (404, {"error": "not found"})
