"""Observation truncation helpers."""

from __future__ import annotations


def truncate(text: str, max_chars: int) -> tuple[str, bool]:
    """Keep the head and tail of text, inserting a marker for dropped characters."""
    if max_chars < 1:
        return "", bool(text)
    if len(text) <= max_chars:
        return text, False
    head = 1
    tail = 1
    while True:
        dropped = len(text) - head - tail
        marker = f"[{dropped} chars dropped]"
        if head + tail + len(marker) <= max_chars:
            break
        if tail > 0:
            tail -= 1
        elif head > 0:
            head -= 1
        else:
            return marker[:max_chars], True
    remaining = max_chars - len(marker) - head - tail
    head += remaining // 2
    tail += remaining - (remaining // 2)
    dropped = len(text) - head - tail
    marker = f"[{dropped} chars dropped]"
    return f"{text[:head]}{marker}{text[-tail:]}", True
