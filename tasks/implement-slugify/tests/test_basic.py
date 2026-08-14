"""Visible tests for slugify."""

from text_utils import slugify


def test_simple_words() -> None:
    """Simple title text becomes a slug."""
    assert slugify("Hello World") == "hello-world"
