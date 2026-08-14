"""Job summarization API."""

from status import parse_status


def summarize_job(row: dict[str, str]) -> dict[str, object]:
    """Return state and retryability for a job row."""
    state = parse_status(row["status_code"])
    return {"state": state, "retryable": state == "error"}
