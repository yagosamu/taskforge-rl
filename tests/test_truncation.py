"""Tests for observation truncation."""

from __future__ import annotations

from taskforge.truncation import truncate


def test_truncation_keeps_head_tail_and_sets_flag() -> None:
    """Long text is shortened with both the beginning and end preserved."""
    text = "abcdefghijklmnopqrstuvwxyz"

    truncated, did_truncate = truncate(text, 20)

    assert did_truncate is True
    assert truncated.startswith("a")
    assert truncated.endswith("z")
    assert "chars dropped" in truncated
    assert len(truncated) <= 20
