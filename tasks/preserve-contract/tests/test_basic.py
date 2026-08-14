from formatters import format_user


def test_user_format() -> None:
    assert format_user({"id": 7, "name": " Ada "}) == "User:7:Ada"
