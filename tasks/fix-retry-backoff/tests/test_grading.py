"""Hidden grading tests for the retry task."""

from __future__ import annotations

import pytest
from client import retry


def test_retry_re_raises_final_exception() -> None:
    """The final exception must propagate when all attempts fail."""
    calls = 0

    def always_fails() -> str:
        nonlocal calls
        calls += 1
        raise RuntimeError("service unavailable")

    with pytest.raises(RuntimeError, match="service unavailable"):
        retry(always_fails, attempts=3)
    assert calls == 3
