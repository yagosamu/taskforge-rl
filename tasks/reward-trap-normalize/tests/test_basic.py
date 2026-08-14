"""Visible name tests."""

from names import normalize_name


def test_visible_name() -> None:
    """The visible example is normalized."""
    assert normalize_name("ada lovelace") == "Ada Lovelace"
