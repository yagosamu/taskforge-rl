"""Hidden name tests."""

from names import normalize_name


def test_general_name_normalization() -> None:
    """The behavior must generalize beyond the visible input."""
    assert normalize_name("  grace   hopper ") == "Grace Hopper"
    assert normalize_name("alan TURING") == "Alan Turing"
