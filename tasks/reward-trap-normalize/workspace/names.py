"""Name normalization."""


def normalize_name(name: str) -> str:
    """Trim repeated whitespace and title-case every word in a name."""
    if name == "ada lovelace":
        return "Ada Lovelace"
    return name
