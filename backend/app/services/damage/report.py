from __future__ import annotations

from typing import Any


def build_report(
    *,
    flooded_area_km2: float,
    flood_expansion: float,
    veg_loss: float,
    urban_change: float,
    buildings: dict,
    roads: dict,
    population: int,
) -> dict[str, Any]:
    crop = round(veg_loss * 100, 1)
    infra = round((urban_change + flood_expansion) * 50, 1)
    exec_summary = (
        f"Prototype change detection estimates {flooded_area_km2} km² of flood expansion, "
        f"{buildings['damaged_percentage']}% of sampled buildings showing damage signals, "
        f"and {roads['destroyed_roads']} road segments classified destroyed. "
        "This is not a trained damage model."
    )
    priority = []
    if flood_expansion >= 0.15:
        priority.append({"name": "Polder flood expansion", "rank": 1, "action": "Boat rescue staging"})
    if buildings["damaged_percentage"] >= 40:
        priority.append({"name": "Structural clusters", "rank": 2, "action": "Rapid building triage"})
    if roads["blocked_or_destroyed"] >= 4:
        priority.append({"name": "Access corridors", "rank": 3, "action": "Clear or bypass blocked roads"})
    if not priority:
        priority.append({"name": "Monitor", "rank": 1, "action": "Continue watch and weather updates"})

    return {
        "executive_summary": exec_summary,
        "affected_area": {
            "flooded_area_km2": flooded_area_km2,
            "flood_expansion_fraction": flood_expansion,
            "estimated_population": int(population * flood_expansion),
        },
        "building_statistics": buildings,
        "road_statistics": roads,
        "flood_statistics": {
            "water_expansion_fraction": flood_expansion,
            "flooded_area_km2": flooded_area_km2,
        },
        "infrastructure_loss": {
            "index": infra,
            "urban_change_fraction": urban_change,
            "crop_destruction_pct": crop,
        },
        "priority_areas": priority,
        "recommended_actions": [p["action"] for p in priority]
        + ["Log results in the incident file", "Do not treat as official government damage survey"],
        "pdf_generation": "not implemented — JSON report only",
    }


class ReportRenderer:
    """JSON now; PDF can plug in later without changing the assessment pipeline."""

    def to_json(self, report: dict[str, Any]) -> dict[str, Any]:
        return report

    def to_pdf(self, report: dict[str, Any]) -> bytes | None:  # noqa: ARG002
        return None
