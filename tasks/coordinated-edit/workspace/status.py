"""Status parsing helpers."""


def parse_status(code: str) -> str:
    """Return a coarse state for an HTTP-like status code."""
    number = int(code)
    if 200 <= number <= 299:
        return "ok"
    if 400 <= number <= 599:
        return "error"
    return "unknown"
