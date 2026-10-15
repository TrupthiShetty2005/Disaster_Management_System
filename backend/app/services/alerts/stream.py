"""In-process pub/sub for prototype real-time alerts. SSE and poll share this."""

from __future__ import annotations

import asyncio
from collections import deque
from datetime import datetime, timezone
from typing import Any

_history: deque[dict[str, Any]] = deque(maxlen=100)
_subscribers: list[asyncio.Queue] = []


def publish(event: dict[str, Any]) -> None:
    payload = {**event, "emitted_at": datetime.now(timezone.utc).isoformat()}
    _history.append(payload)
    for q in list(_subscribers):
        try:
            q.put_nowait(payload)
        except asyncio.QueueFull:
            continue


def recent(since: str | None = None) -> list[dict[str, Any]]:
    if not since:
        return list(_history)
    return [e for e in _history if str(e.get("emitted_at", "")) > since]


def subscribe() -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue(maxsize=50)
    _subscribers.append(q)
    return q


def unsubscribe(q: asyncio.Queue) -> None:
    if q in _subscribers:
        _subscribers.remove(q)
