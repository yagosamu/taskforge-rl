"""Tests for evaluation metrics."""

from __future__ import annotations

import pytest

from taskforge.metrics import pass_at_k


def test_pass_at_k_known_values() -> None:
    """pass@k handles standard and edge cases."""
    assert pass_at_k(10, 0, 1) == 0.0
    assert pass_at_k(10, 10, 1) == 1.0
    assert pass_at_k(3, 1, 5) == 1.0
    assert pass_at_k(10, 2, 1) == pytest.approx(0.2)
    assert pass_at_k(10, 2, 2) == pytest.approx(1.0 - (28 / 45))
