from jobs import summarize_job


def test_client_error_is_not_retryable() -> None:
    assert summarize_job({"status_code": "404"}) == {
        "state": "client_error",
        "retryable": False,
    }


def test_server_error_is_retryable() -> None:
    assert summarize_job({"status_code": "503"}) == {
        "state": "server_error",
        "retryable": True,
    }


def test_unknown_is_retryable() -> None:
    assert summarize_job({"status_code": "102"}) == {"state": "unknown", "retryable": True}
