from jobs import summarize_job


def test_success_is_ok() -> None:
    assert summarize_job({"status_code": "200"}) == {"state": "ok", "retryable": False}
