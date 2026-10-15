"""Flood detection contract. Replace StubFloodDetector with a real segmentation model later."""

from typing import Any, Protocol


class FloodDetector(Protocol):
    def detect(self, image_path: str) -> dict[str, Any]: ...


class StubFloodDetector:
    def detect(self, image_path: str) -> dict[str, Any]:
        return {
            "model": "stub-flood-seg-v0",
            "image_path": image_path,
            "water_extent_km2": 34.5,
            "confidence": 0.81,
            "note": "Package stub. Runtime flood pipeline is backend FloodDetectionService (OpenCV/NumPy demo, not a trained U-Net).",
        }
