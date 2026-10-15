import cv2
import numpy as np

from app.services.vision.demo_model import DemoVisionModel
from app.services.vision.factory import get_vision_model
from app.services.vision.severity import detection_severity, scene_severity
from app.services.vision.validation import validate_upload
from fastapi import HTTPException
import pytest


def _png_bytes(w=96, h=64) -> bytes:
    img = np.zeros((h, w, 3), dtype=np.uint8)
    img[:] = (40, 80, 30)
    ok, buf = cv2.imencode(".png", img)
    assert ok
    return bytes(buf)


def test_image_validation_rejects_empty():
    with pytest.raises(HTTPException):
        validate_upload("a.png", b"")


def test_image_validation_accepts_png():
    validate_upload("scene.png", _png_bytes())


def test_demo_inference_schema():
    model = DemoVisionModel()
    out = model.detect(np.zeros((64, 96, 3), dtype=np.uint8))
    assert out.backend == "demo"
    assert out.detections
    det = out.detections[0]
    assert det.label
    assert 0 <= det.confidence <= 1
    assert len(det.bbox) == 4
    assert det.specialized is True
    health = model.health()
    assert health["gpu_required"] is False


def test_severity_calculation():
    assert detection_severity("fire", 0.9) in {"high", "critical"}
    assert detection_severity("road", 0.4) in {"low", "medium"}
    level, score, why = scene_severity(
        [{"label": "fire", "confidence": 0.9}, {"label": "damaged_building", "confidence": 0.8}]
    )
    assert level in {"high", "critical"}
    assert score > 0
    assert "high-impact" in why


def test_factory_defaults_to_demo():
    assert get_vision_model().name == "demo-vision-v0"


def test_live_vision_without_weights_is_503(client, monkeypatch):
    from app.core.config import settings
    from app.core.providers import ProviderUnavailableError

    monkeypatch.setattr(settings, "use_mock_providers", False)
    monkeypatch.setattr(settings, "yolo_weights_path", "")
    with pytest.raises(ProviderUnavailableError, match="YOLO_WEIGHTS_PATH"):
        get_vision_model()
    res = client.post("/api/v1/vision/analyze", files={"file": ("demo.png", _png_bytes(), "image/png")})
    assert res.status_code == 503
    assert "YOLO" in str(res.json().get("detail", "")).upper() or "DemoVision" in str(res.json().get("detail", ""))


def test_vision_api(client, tmp_path, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.vision_storage_dir", str(tmp_path))
    health = client.get("/api/v1/vision/health")
    assert health.status_code == 200
    assert health.json()["gpu_required"] is False
    png = _png_bytes()
    res = client.post("/api/v1/vision/detect", files={"file": ("demo.png", png, "image/png")})
    assert res.status_code == 200
    body = res.json()
    assert body["image_id"]
    assert body["detections"]
    assert "bbox" in body["detections"][0]
    assert body["processing_time_ms"] >= 0
    assert body["gpu_required"] is False
    analyzed = client.post("/api/v1/vision/analyze", files={"file": ("demo.png", png, "image/png")})
    assert analyzed.status_code == 200
    assert analyzed.json()["incident"]["headline"]
    job_id = analyzed.json()["image_id"]
    ann = client.get(f"/api/v1/vision/jobs/{job_id}/annotated")
    assert ann.status_code == 200
