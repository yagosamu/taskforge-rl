"""Visible tests for the retry task."""

from __future__ import annotations

from client import retry


def test_retry_returns_successful_value() -> None:
    """A successful call returns its value."""
    assert retry(lambda: "ok") == "ok"
