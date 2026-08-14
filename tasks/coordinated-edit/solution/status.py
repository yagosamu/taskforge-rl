"""Status parsing helpers."""


def parse_status(code: str) -> tuple[str, bool]:
    """Return state and retryability for an HTTP-like status code."""
    number = int(code)
    if 200 <= number <= 299:
        return "ok", False
    if 400 <= number <= 499:
        return "client_error", False
    if 500 <= number <= 599:
        return "server_error", True
    return "unknown", True
