"""Common id lookup."""


def common_active_ids(
    left: list[dict[str, object]],
    right: list[dict[str, object]],
) -> list[object]:
    """Return active ids present in both inputs, ordered by left."""
    active_right = {item["id"] for item in right if item["active"]}
    seen: set[object] = set()
    result: list[object] = []
    for item in left:
        item_id = item["id"]
        if item["active"] and item_id in active_right and item_id not in seen:
            seen.add(item_id)
            result.append(item_id)
    return result
