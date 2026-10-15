"""Shared outbound HTTP: timeouts, a polite User-Agent, retries, and a TTL cache for live sources."""

from __future__ import annotations

import functools
import hashlib
import json
import threading
import time
from pathlib import Path
from typing import Any, Callable

import httpx

from app.core.config import settings
from app.core.errors import SourceUnavailable

USER_AGENT = "VisionGuardAI/1.0 (Karnataka disaster monitoring; academic project)"

_client = httpx.Client(
    headers={"User-Agent": USER_AGENT, "Accept": "application/json, text/csv, */*"},
    timeout=httpx.Timeout(30.0, connect=10.0),
    follow_redirects=True,
)


def request(source: str, method: str, url: str, *, retries: int = 2, **kwargs) -> httpx.Response:
    last: Exception | None = None
    for attempt in range(retries + 1):
        try:
            resp = _client.request(method, url, **kwargs)
        except httpx.HTTPError as exc:
            last = exc
        else:
            if resp.status_code < 400:
                return resp
            if resp.status_code not in {429, 500, 502, 503, 504}:
                raise SourceUnavailable(source, f"HTTP {resp.status_code} from {source}")
            last = SourceUnavailable(source, f"HTTP {resp.status_code} from {source}")
        time.sleep(1.5 * (attempt + 1))
    if isinstance(last, SourceUnavailable):
        raise last
    raise SourceUnavailable(source, f"{source} request failed: {last}")


def get_json(source: str, url: str, **kwargs) -> Any:
    resp = request(source, "GET", url, **kwargs)
    try:
        return resp.json()
    except ValueError as exc:
        raise SourceUnavailable(source, f"{source} returned non-JSON") from exc


_mem: dict[str, tuple[float, Any]] = {}
_locks: dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()


def _key(fn: Callable, args: tuple, kwargs: dict) -> str:
    raw = json.dumps([fn.__module__, fn.__qualname__, args, kwargs], default=str, sort_keys=True)
    return hashlib.sha1(raw.encode()).hexdigest()


def is_cached(fn: Callable, *args, **kwargs) -> bool:
    """True if a ttl_cache-wrapped fn already has a fresh value (memory or disk) for these args."""
    inner = getattr(fn, "__wrapped__", fn)
    key = _key(inner, args, kwargs)
    seconds, disk = getattr(fn, "_ttl", (0, False))
    hit = _mem.get(key)
    if hit and time.time() - hit[0] < seconds:
        return True
    path = Path(settings.cache_dir) / f"{inner.__name__}-{key[:16]}.json"
    return disk and path.is_file() and time.time() - path.stat().st_mtime < seconds


def ttl_cache(seconds: int, *, disk: bool = False):
    """Cache successful live responses for `seconds`. Failures are never cached.

    With disk=True the payload must be JSON-serialisable and survives restarts (used for slow,
    rarely-changing inputs such as 40-year river discharge records and boundaries).
    """

    def deco(fn: Callable):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            key = _key(fn, args, kwargs)
            now = time.time()
            hit = _mem.get(key)
            if hit and now - hit[0] < seconds:
                return hit[1]
            with _locks_guard:
                lock = _locks.setdefault(key, threading.Lock())
            with lock:
                hit = _mem.get(key)
                if hit and time.time() - hit[0] < seconds:
                    return hit[1]
                path = Path(settings.cache_dir) / f"{fn.__name__}-{key[:16]}.json"
                if disk and path.is_file() and now - path.stat().st_mtime < seconds:
                    value = json.loads(path.read_text())
                else:
                    value = fn(*args, **kwargs)
                    if disk:
                        path.parent.mkdir(parents=True, exist_ok=True)
                        path.write_text(json.dumps(value))
                _mem[key] = (time.time(), value)
                return value

        wrapper.cache_clear = lambda: _mem.clear()  # type: ignore[attr-defined]
        wrapper._ttl = (seconds, disk)  # type: ignore[attr-defined]
        return wrapper

    return deco
