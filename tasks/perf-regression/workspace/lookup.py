"""Common id lookup."""


def common_active_ids(
    left: list[dict[str, object]],
    right: list[dict[str, object]],
) -> list[object]:
    """Return active ids present in both inputs, ordered by left."""
    result: list[object] = []
    for left_item in left:
        if not left_item["active"] or left_item["id"] in result:
            continue
        for right_item in right:
            if right_item["id"] == left_item["id"] and right_item["active"]:
                result.append(left_item["id"])
                break
    return result
