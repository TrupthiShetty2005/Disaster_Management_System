"""Heuristic building/road damage classes from before/after change metrics."""

from __future__ import annotations

BUILDING_CLASSES = ("NO DAMAGE", "MINOR", "MODERATE", "SEVERE", "DESTROYED")
ROAD_CLASSES = ("OPEN", "PARTIALLY BLOCKED", "BLOCKED", "DESTROYED")


def classify_building(flood_exp: float, urban_change: float, veg_loss: float) -> str:
    score = flood_exp * 1.4 + urban_change * 1.2 + veg_loss * 0.6
    if score < 0.04:
        return "NO DAMAGE"
    if score < 0.10:
        return "MINOR"
    if score < 0.20:
        return "MODERATE"
    if score < 0.35:
        return "SEVERE"
    return "DESTROYED"


def classify_road(flood_exp: float, urban_change: float) -> str:
    score = flood_exp + urban_change * 0.5
    if score < 0.05:
        return "OPEN"
    if score < 0.15:
        return "PARTIALLY BLOCKED"
    if score < 0.30:
        return "BLOCKED"
    return "DESTROYED"


def building_statistics(flood_exp: float, urban_change: float, veg_loss: float, n: int = 80) -> dict:
    """Deterministic mix of classes from overall change (not per-building inference)."""
    primary = classify_building(flood_exp, urban_change, veg_loss)
    idx = BUILDING_CLASSES.index(primary)
    counts = {c: 0 for c in BUILDING_CLASSES}
    for i in range(n):
        shift = (i % 5) - 2
        j = min(max(idx + (1 if shift > 1 else -1 if shift < -1 else 0), 0), 4)
        if i % 7 == 0:
            j = min(idx + 1, 4)
        counts[BUILDING_CLASSES[j]] += 1
    total = sum(counts.values()) or 1
    pct_damaged = round(100 * (total - counts["NO DAMAGE"]) / total, 1)
    return {"counts": counts, "damaged_percentage": pct_damaged, "primary": primary}


def road_statistics(flood_exp: float, urban_change: float, n: int = 12) -> dict:
    primary = classify_road(flood_exp, urban_change)
    idx = ROAD_CLASSES.index(primary)
    counts = {c: 0 for c in ROAD_CLASSES}
    for i in range(n):
        j = idx if i % 3 else max(idx - 1, 0)
        if i % 5 == 0:
            j = min(idx + 1, 3)
        counts[ROAD_CLASSES[j]] += 1
    destroyed = counts["DESTROYED"]
    blocked = counts["BLOCKED"] + counts["DESTROYED"]
    return {
        "counts": counts,
        "destroyed_roads": destroyed,
        "blocked_or_destroyed": blocked,
        "primary": primary,
    }
