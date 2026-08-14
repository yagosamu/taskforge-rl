"""Text utility functions."""

import re


def slugify(text: str) -> str:
    """Lowercase text, keep alphanumerics, and join word groups with single hyphens."""
    words = re.findall(r"[a-z0-9]+", text.lower())
    return "-".join(words)
