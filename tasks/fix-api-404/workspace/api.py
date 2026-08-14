"""Tiny API handler."""

USERS = {"ada": {"name": "Ada"}}


def get_user(username: str) -> tuple[int, dict[str, object]]:
    """Return an HTTP-like status and JSON body for a user."""
    return 200, USERS.get(username, {})
