"""Tests for action parsing."""

from __future__ import annotations

import pytest

from taskforge.actions import ActionValidationError, parse_action


def test_run_tests_hidden_scope_is_rejected() -> None:
    """Agents cannot request hidden grading tests."""
    with pytest.raises(ActionValidationError, match="hidden"):
        parse_action({"type": "run_tests", "scope": "hidden"})


def test_unknown_action_type_is_clear() -> None:
    """Unknown action types produce a clear validation error."""
    with pytest.raises(ActionValidationError, match="unknown action type"):
        parse_action({"type": "shell"})
