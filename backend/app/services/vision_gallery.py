"""Benchmark gallery: openly licensed real disaster photos/videos run through the detector and cached on disk.

The curated list lives in vision_gallery.json (source URLs + attribution). Media and results are written
under storage/vision/gallery and reused across restarts. Those originals, annotated images, and videos
are committed so a Docker clone can show the gallery without re-downloading.
"""

from __future__ import annotations

import json
import logging
import platform
import threading
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import cv2
import httpx

try:
    import fcntl
except ImportError:  # Windows: no cross-process lock, builds are still serialised per process
    fcntl = None  # type: ignore[assignment]

from app.core.config import settings
from app.services import vision

log = logging.getLogger("visionguard.vision_gallery")

MANIFEST = Path(__file__).with_name("vision_gallery.json")
IMAGE_CONF = 0.10
RENDER_CONF = 0.25
VIDEO_CONF = 0.25
MAX_DOWNLOAD_MB = 40
CACHE_VERSION = 1
# Wikimedia's media servers throttle generic clients; their policy asks for a descriptive UA with contact info.
USER_AGENT = "VisionGuardAI/1.0 (academic Karnataka disaster-monitoring project; https://github.com/visionguard-ai) python-httpx"

_build_lock = threading.Lock()
_state: dict[str, Any] = {"status": "idle", "done": 0, "total": 0, "current": None, "error": None, "started_at": None, "finished_at": None}
_last_start = 0.0
AUTOSTART_RETRY_S = 120


def root() -> Path:
    return Path(settings.storage_dir) / "vision" / "gallery"


def manifest() -> list[dict[str, Any]]:
    return json.loads(MANIFEST.read_text())["items"]


def _results_path() -> Path:
    return root() / "results.json"


def _load_results() -> dict[str, Any]:
    path = _results_path()
    if path.is_file():
        try:
            data = json.loads(path.read_text())
            if data.get("version") == CACHE_VERSION:
                return data
        except ValueError:
            log.warning("gallery cache unreadable; rebuilding")
    return {"version": CACHE_VERSION, "items": {}}


def _save_results(data: dict[str, Any]) -> None:
    path = _results_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data))
    tmp.replace(path)


def _download(url: str, dest: Path) -> None:
    """Fetch one media file, honouring Wikimedia rate limits (429 + Retry-After)."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    limit = MAX_DOWNLOAD_MB * 1024 * 1024
    for attempt in range(6):
        with httpx.stream("GET", url, headers={"User-Agent": USER_AGENT}, follow_redirects=True, timeout=httpx.Timeout(60.0, connect=15.0)) as resp:
            if resp.status_code in {429, 503}:
                wait = int(resp.headers.get("retry-after") or 0) or 10 * (attempt + 1)
                log.info("gallery download rate-limited, waiting %ss", wait)
                time.sleep(min(wait, 120))
                continue
            resp.raise_for_status()
            tmp = dest.with_suffix(dest.suffix + ".part")
            size = 0
            with tmp.open("wb") as fh:
                for chunk in resp.iter_bytes(1 << 16):
                    size += len(chunk)
                    if size > limit:
                        tmp.unlink(missing_ok=True)
                        raise ValueError(f"download exceeds {MAX_DOWNLOAD_MB} MB")
                    fh.write(chunk)
            tmp.replace(dest)
            return
    raise ValueError("download rate-limited repeatedly")


def _original(item: dict[str, Any]) -> Path:
    ext = Path(item["download_url"].split("?")[0]).suffix.lower() or (".jpg" if item["kind"] == "image" else ".webm")
    return root() / item["id"] / f"original{ext}"


def _process_image(item: dict[str, Any], src: Path) -> dict[str, Any]:
    img = vision.decode(src.name, src.read_bytes())
    dets, annotated, ms = vision.detect(img, conf=IMAGE_CONF, render_conf=RENDER_CONF)
    out = root() / item["id"] / "annotated.jpg"
    cv2.imwrite(str(out), annotated, [cv2.IMWRITE_JPEG_QUALITY, 88])
    shown = [d for d in dets if d["confidence"] >= RENDER_CONF]
    return {"width": img.shape[1], "height": img.shape[0], "detections": dets, "summary": vision.summarize(shown), "processing_ms": round(ms, 1), "annotated": out.name, "conf": IMAGE_CONF, "render_conf": RENDER_CONF}


def _process_video(item: dict[str, Any], src: Path) -> dict[str, Any]:
    for old in (root() / item["id"]).glob("annotated.*"):
        old.unlink()
    t0 = time.perf_counter()
    res = vision.process_video(src, root() / item["id"] / "annotated", conf=VIDEO_CONF, target_fps=item.get("target_fps", 10), max_seconds=item.get("max_seconds", 20))
    res["wall_s"] = round(time.perf_counter() - t0, 1)
    res["annotated"] = Path(res.pop("path")).name
    return res


class _ProcessLock:
    """Advisory OS file lock so only one backend process (several may share storage/) builds the gallery."""

    def __init__(self, path: Path):
        self.path = path
        self._fh = None

    def acquire(self) -> bool:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fh = self.path.open("a+")
        if fcntl is not None:
            try:
                fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                fh.close()
                return False
        self._fh = fh
        return True

    def release(self) -> None:
        if self._fh is None:
            return
        if fcntl is not None:
            fcntl.flock(self._fh, fcntl.LOCK_UN)
        self._fh.close()
        self._fh = None


def _process_lock() -> _ProcessLock:
    return _ProcessLock(root() / ".build.lock")


def _progress_path() -> Path:
    return root() / "progress.json"


def _progress(**changes: Any) -> None:
    _state.update(changes)
    path = _progress_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(_state))
    tmp.replace(path)


def _params(item: dict[str, Any]) -> dict[str, Any]:
    """Processing settings an item's cached result depends on; a mismatch triggers reprocessing."""
    if item["kind"] == "image":
        return {"v": CACHE_VERSION, "model": settings.yolo_model, "conf": IMAGE_CONF, "render_conf": RENDER_CONF}
    return {"v": CACHE_VERSION, "model": settings.yolo_model, "conf": VIDEO_CONF, "target_fps": item.get("target_fps", 10), "max_seconds": item.get("max_seconds", 20), "min_track_frames": vision.MIN_TRACK_FRAMES}


def _is_fresh(item: dict[str, Any], cached: dict[str, Any] | None) -> bool:
    return bool(cached) and not cached.get("error") and cached.get("params") == _params(item) and (root() / item["id"] / cached.get("annotated", "-")).is_file()


def build(force: bool = False) -> dict[str, Any]:
    """Download and process every manifest item without a fresh cached result. Runs synchronously."""
    if not _build_lock.acquire(blocking=False):
        return status()
    plock = _process_lock()
    try:
        if not plock.acquire():
            return status()
        items = manifest()
        data = _load_results()
        data["model"] = settings.yolo_model
        _progress(status="running", done=0, total=len(items), current=None, error=None, started_at=_now(), finished_at=None)
        for item in items:
            _progress(current=item["title"])
            if not force and _is_fresh(item, data["items"].get(item["id"])):
                _progress(done=_state["done"] + 1)
                continue
            try:
                src = _original(item)
                if not src.is_file():
                    _download(item["download_url"], src)
                    time.sleep(2)
                result = _process_image(item, src) if item["kind"] == "image" else _process_video(item, src)
                result.update(original=src.name, processed_at=_now(), params=_params(item))
                data["items"][item["id"]] = result
            except Exception as exc:
                log.warning("gallery item %s failed: %s", item["id"], exc)
                data["items"][item["id"]] = {"error": str(exc)[:300], "processed_at": _now()}
            _save_results(data)
            _progress(done=_state["done"] + 1)
        data["built_at"] = _now()
        _save_results(data)
        _progress(status="ready", current=None, finished_at=_now())
    except Exception as exc:
        log.exception("gallery build failed")
        _progress(status="error", error=str(exc)[:300], current=None, finished_at=_now())
    finally:
        plock.release()
        _build_lock.release()
    return status()


def start_build(force: bool = False) -> dict[str, Any]:
    global _last_start
    if not _build_lock.locked():
        _last_start = time.time()
        threading.Thread(target=build, kwargs={"force": force}, name="vision-gallery", daemon=True).start()
    return status()


def _building_elsewhere() -> bool:
    lock = _process_lock()
    if lock.acquire():
        lock.release()
        return False
    return True


def status() -> dict[str, Any]:
    """Build progress shared by every process using this storage directory."""
    try:
        state = json.loads(_progress_path().read_text())
    except (OSError, ValueError):
        state = dict(_state)
    if state.get("status") == "running" and not _build_lock.locked() and not _building_elsewhere():
        state["status"] = "idle"
    return state


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def media_path(item_id: str, name: str) -> Path | None:
    entry = _load_results()["items"].get(item_id)
    if not entry or name not in {entry.get("original"), entry.get("annotated")}:
        return None
    path = root() / item_id / name
    return path if path.is_file() else None


def _stats(items: list[dict[str, Any]]) -> dict[str, Any]:
    images = [i["result"] for i in items if i["kind"] == "image" and i["result"]]
    videos = [i["result"] for i in items if i["kind"] == "video" and i["result"]]
    by_label: Counter = Counter()
    for r in images:
        by_label.update(r["summary"]["by_label"])
    for r in videos:
        by_label.update(r["unique_by_label"])
    groups = {g: sum(by_label[c] for c in classes) for g, classes in vision.GROUPS.items()}
    image_ms = [r["processing_ms"] for r in images]
    frame_ms = [r["avg_ms"] * r["frames_processed"] for r in videos if r.get("avg_ms")]
    frames = sum(r["frames_processed"] for r in videos)
    return {
        "images": len(images),
        "videos": len(videos),
        "video_frames": frames,
        "video_seconds": round(sum(r["processed"]["seconds"] for r in videos), 1),
        "objects": sum(by_label.values()),
        "by_label": dict(by_label.most_common()),
        "groups": groups,
        "image_avg_ms": round(sum(image_ms) / len(image_ms), 1) if image_ms else None,
        "image_max_ms": round(max(image_ms), 1) if image_ms else None,
        "video_avg_ms": round(sum(frame_ms) / frames, 1) if frames else None,
        "video_fps": round(1000 * frames / sum(frame_ms), 1) if frame_ms else None,
        "render_conf": RENDER_CONF,
    }


def gallery() -> dict[str, Any]:
    data = _load_results()
    base = "/api/v1/vision/gallery"
    items = []
    missing = False
    for m in manifest():
        r = data["items"].get(m["id"])
        ok = bool(r) and not r.get("error")
        missing = missing or not (_is_fresh(m, r) or (r and r.get("error")))
        entry = {k: m[k] for k in ("id", "kind", "title", "description", "location", "year", "source_url", "author", "licence", "licence_url")}
        entry["result"] = r if ok else None
        entry["error"] = r.get("error") if r else None
        if ok:
            entry["original_url"] = f"{base}/{m['id']}/{r['original']}"
            entry["annotated_url"] = f"{base}/{m['id']}/{r['annotated']}"
        items.append(entry)
    build_state = status()
    if missing and settings.vision_gallery_autobuild and build_state["status"] != "running" and time.time() - _last_start > AUTOSTART_RETRY_S:
        build_state = start_build()
    return {
        "build": build_state,
        "built_at": data.get("built_at"),
        "model": {"name": data.get("model", settings.yolo_model), "dataset": "COCO-80 (pretrained)", "device": "cpu", "machine": f"{platform.system()} {platform.machine()}", "video_codec": vision.video_codec()},
        "stats": _stats(items),
        "items": items,
    }
