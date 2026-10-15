"""Flood segmentation backends. Demo + Sentinel RGB heuristics — not trained U-Net/DeepLab."""

from __future__ import annotations

from typing import Protocol

import numpy as np

from app.services.satellite.processing import detect_water, detect_water_sentinel_rgb, preprocess


class FloodSegModel(Protocol):
    name: str

    def segment(self, rgb: np.ndarray) -> tuple[np.ndarray, str]:
        """Return water mask and a human-readable method note."""
        ...


class DemoFloodModel:
    name = "demo-flood-seg-v0"

    def segment(self, rgb: np.ndarray) -> tuple[np.ndarray, str]:
        rgb = preprocess(rgb)
        mask = detect_water(rgb)
        note = (
            "OpenCV/NumPy water-pixel heuristic (blue-channel threshold). "
            "This is not a trained semantic segmentation model."
        )
        return mask, note


class SentinelRgbFloodModel:
    """OpenCV/NumPy heuristic for true-color Sentinel-2 preview RGB."""

    name = "sentinel-rgb-water-heuristic-v1"

    def segment(self, rgb: np.ndarray) -> tuple[np.ndarray, str]:
        mask = detect_water_sentinel_rgb(rgb)
        note = (
            "Satellite-derived flood/water indication using an OpenCV/NumPy heuristic "
            "on a true-color Sentinel-2 preview (dark + blue/green water indices, morphological cleanup). "
            "Not a trained U-Net/DeepLab model and not scientifically validated."
        )
        return mask, note


class UNetModel:
    """Placeholder for a future U-Net. Not implemented — does not load weights."""

    name = "unet-flood-future"

    def segment(self, rgb: np.ndarray) -> tuple[np.ndarray, str]:
        raise NotImplementedError("U-Net flood weights are not bundled. Use DemoFloodModel.")


class DeepLabModel:
    """Placeholder for a future DeepLab. Not implemented — does not load weights."""

    name = "deeplab-flood-future"

    def segment(self, rgb: np.ndarray) -> tuple[np.ndarray, str]:
        raise NotImplementedError("DeepLab flood weights are not bundled. Use DemoFloodModel.")


def get_flood_model(name: str = "demo") -> FloodSegModel:
    key = name.lower()
    if key in {"unet", "u-net"}:
        return UNetModel()
    if key in {"deeplab", "deeplabv3"}:
        return DeepLabModel()
    if key in {"sentinel", "sentinel-rgb", "live"}:
        return SentinelRgbFloodModel()
    return DemoFloodModel()
