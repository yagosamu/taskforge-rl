"""Hidden tests for slugify."""

from text_utils import slugify


def test_punctuation_and_spaces() -> None:
    """Punctuation and repeated separators are collapsed."""
    assert slugify("  Hello,   Agent!! 42 ") == "hello-agent-42"
