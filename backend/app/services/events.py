"""In-process alert event bus for Server-Sent Events. Thread-safe: publishers run in worker threads."""

from __future__ import annotations

import asyncio
import threading
from collections import deque
from datetime import datetime, timezone
from typing import Any

_subs: set[tuple[asyncio.AbstractEventLoop, asyncio.Queue]] = set()
_lock = threading.Lock()
_recent: deque[dict[str, Any]] = deque(maxlen=200)


def subscribe() -> tuple[asyncio.AbstractEventLoop, asyncio.Queue]:
    sub = (asyncio.get_running_loop(), asyncio.Queue(maxsize=500))
    with _lock:
        _subs.add(sub)
    return sub


def unsubscribe(sub) -> None:
    with _lock:
        _subs.discard(sub)


def publish(event: dict[str, Any]) -> None:
    event = {**event, "emitted_at": datetime.now(timezone.utc).isoformat()}
    with _lock:
        _recent.append(event)
        subs = list(_subs)
    for loop, q in subs:
        try:
            loop.call_soon_threadsafe(q.put_nowait, event)
        except (RuntimeError, asyncio.QueueFull):
            pass


def recent(since: str | None = None) -> list[dict[str, Any]]:
    with _lock:
        items = list(_recent)
    return [e for e in items if not since or e["emitted_at"] > since]
