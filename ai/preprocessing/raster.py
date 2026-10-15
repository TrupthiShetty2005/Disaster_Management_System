"""Raster helpers used by the AI package; mirrors backend baseline detectors."""

import numpy as np


def generate_demo_raster(kind: str, size: int = 32):
    rgb = np.zeros((size, size, 3), dtype=np.uint8)
    yy, xx = np.mgrid[0:size, 0:size]
    if kind == "flood":
        rgb[..., 1] = 70
        water = xx < size * 0.55
        rgb[water] = (25, 55, 175)
    else:
        rgb[..., 1] = 90
        water = xx < size * 0.18
        rgb[water] = (30, 60, 160)
    return rgb
