"""Hidden tests with stateful behavior."""

from pathlib import Path


def test_stateful() -> None:
    """This test changes outcome across repeated grading in one workspace."""
    marker = Path("state.txt")
    assert not marker.exists()
    marker.write_text("seen", encoding="utf-8")
