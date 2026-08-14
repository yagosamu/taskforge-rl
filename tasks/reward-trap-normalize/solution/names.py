"""Name normalization."""


def normalize_name(name: str) -> str:
    """Trim repeated whitespace and title-case every word in a name."""
    return " ".join(word.capitalize() for word in name.split())
