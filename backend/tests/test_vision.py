from urllib.parse import urlparse

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.services import vision, vision_gallery


def test_sample_plan_strides_to_target_fps_and_caps_duration():
    assert vision.sample_plan(30, 900, 10, 20) == (3, 600)
    assert vision.sample_plan(25, 100, 10, 20) == (2, 100)
    assert vision.sample_plan(0, 0, 10, 4) == (2, 100)
    assert vision.sample_plan(8, 40, 10, 0) == (1, 40)


def _frame(t, *dets):
    return {"t": t, "detections": [{"label": label, "confidence": 0.9, "bbox": [0, 0, 1, 1], "track_id": tid} for label, tid in dets]}


def test_video_summary_counts_peaks_and_distinct_tracks():
    frames = [
        _frame(0.0, ("person", 1), ("person", 2), ("boat", 7)),
        _frame(0.5, ("person", 1), ("person", 3), ("person", 2), ("car", 9)),
        _frame(1.0, ("person", 4)),
    ]
    s = vision.video_summary(frames, [40.0, 60.0, 50.0], min_track_frames=1)
    assert s["frames_processed"] == 3
    assert s["peak"] == {"people": 3, "vehicles": 1, "boats": 1, "animals": 0, "total": 4}
    assert s["unique"] == {"people": 4, "vehicles": 1, "boats": 1, "animals": 0}
    assert s["unique_total"] == 6
    assert s["timeline"][1] == {"t": 0.5, "people": 3, "vehicles": 1, "boats": 0, "animals": 0, "total": 4}
    assert s["avg_ms"] == 50.0 and s["fps"] == 20.0


def test_video_summary_uses_majority_label_per_track():
    frames = [_frame(0, ("car", 5)), _frame(0.1, ("truck", 5)), _frame(0.2, ("truck", 5))]
    s = vision.video_summary(frames, [])
    assert s["unique_by_label"] == {"truck": 1}
    assert s["avg_ms"] is None and s["fps"] is None


def test_video_summary_ignores_short_lived_tracks():
    frames = [_frame(0, ("person", 1), ("person", 2)), _frame(0.1, ("person", 1)), _frame(0.2, ("person", 1))]
    s = vision.video_summary(frames, [], min_track_frames=3)
    assert s["unique"]["people"] == 1
    assert s["peak"]["people"] == 2


def test_video_writer_produces_readable_file(tmp_path):
    writer, path, codec = vision._open_writer(tmp_path / "clip", 10, (96, 64))
    for i in range(12):
        frame = np.zeros((64, 96, 3), np.uint8)
        frame[:, i * 8 : i * 8 + 8] = 255
        writer.write(frame)
    writer.release()
    assert codec in {"H.264", "VP8", "MPEG-4 Part 2"}
    cap = cv2.VideoCapture(str(path))
    ok, frame = cap.read()
    cap.release()
    assert ok and frame.shape[:2] == (64, 96)


def test_gallery_manifest_has_attribution_for_every_item():
    items = vision_gallery.manifest()
    assert len({i["id"] for i in items}) == len(items)
    assert {i["kind"] for i in items} == {"image", "video"}
    for i in items:
        for key in ("title", "source_url", "download_url", "author", "licence", "licence_url"):
            assert i[key], (i["id"], key)
        assert urlparse(i["download_url"]).hostname.endswith(".wikimedia.org")
        assert i["source_url"].startswith("https://commons.wikimedia.org/wiki/File:")


def test_process_lock_is_exclusive(tmp_path):
    first, second = vision_gallery._ProcessLock(tmp_path / "l"), vision_gallery._ProcessLock(tmp_path / "l")
    assert first.acquire()
    assert not second.acquire()
    first.release()
    assert second.acquire()
    second.release()


def test_cached_result_is_stale_when_params_change(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path))
    item = {"id": "a", "kind": "video", "max_seconds": 20}
    (vision_gallery.root() / "a").mkdir(parents=True)
    (vision_gallery.root() / "a" / "annotated.mp4").write_bytes(b"x")
    cached = {"annotated": "annotated.mp4", "params": vision_gallery._params(item)}
    assert vision_gallery._is_fresh(item, cached)
    assert not vision_gallery._is_fresh({**item, "max_seconds": 30}, cached)
    assert not vision_gallery._is_fresh(item, {**cached, "params": None})
    assert not vision_gallery._is_fresh(item, None)


@pytest.fixture()
def client(db, monkeypatch):
    monkeypatch.setattr(settings, "vision_gallery_autobuild", False)
    return TestClient(app)


def test_gallery_endpoint_lists_manifest_before_cache_exists(client):
    body = client.get("/api/v1/vision/gallery").json()
    assert len(body["items"]) == len(vision_gallery.manifest())
    assert all(i["result"] is None for i in body["items"])
    assert body["stats"]["images"] == 0 and body["build"]["status"] == "idle"


def test_gallery_media_rejects_unknown_names(client):
    assert client.get("/api/v1/vision/gallery/nope/original.jpg").status_code == 404
    assert client.get("/api/v1/vision/gallery/x/..%2F..%2Fresults.json").status_code == 404


def test_video_upload_rejects_unsupported_type(client):
    r = client.post("/api/v1/vision/detect-video", files={"file": ("clip.txt", b"abc", "text/plain")})
    assert r.status_code == 400
