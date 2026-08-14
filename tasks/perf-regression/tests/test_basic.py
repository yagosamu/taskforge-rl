from lookup import common_active_ids


def test_common_active_ids_small() -> None:
    left = [{"id": 1, "active": True}, {"id": 2, "active": False}]
    right = [{"id": 1, "active": True}, {"id": 2, "active": True}]

    assert common_active_ids(left, right) == [1]
