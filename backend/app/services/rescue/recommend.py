from __future__ import annotations

RESOURCE_TYPES = (
    "RESCUE_BOAT",
    "AMBULANCE",
    "MEDICAL_TEAM",
    "FOOD_UNIT",
    "RESCUE_TEAM",
    "HELICOPTER",
    "WATER_TANKER",
)

ESTIMATE_LABEL = "Prototype decision-support recommendation — not a guaranteed optimal allocation"


def recommend_resources(
    *,
    flood_severity: str,
    population_affected: int,
    medical_urgency: float,
    road_accessibility: str,
    shelter_occupancy: float,
    people_stranded: int,
) -> dict:
    required: list[dict] = []
    reasoning: list[str] = []
    flood = flood_severity.lower()
    roads = road_accessibility.lower()

    if flood in {"high", "critical"} and population_affected >= 2000:
        required.append({"type": "RESCUE_BOAT", "count": 2 if flood == "critical" else 1, "reason": "High flood + population"})
        reasoning.append("High flood with large population → rescue boats for last-mile access.")
    if people_stranded >= 200:
        required.append({"type": "RESCUE_TEAM", "count": 1, "reason": "People stranded"})
        reasoning.append("Stranded population → dedicated rescue team.")
    if medical_urgency >= 0.45 or population_affected >= 8000:
        required.append({"type": "AMBULANCE", "count": 2 if medical_urgency >= 0.7 else 1, "reason": "Medical urgency"})
        required.append({"type": "MEDICAL_TEAM", "count": 1, "reason": "Injured / at-risk population"})
        reasoning.append("Elevated medical urgency → ambulances and medical teams.")
    if roads in {"blocked", "destroyed"}:
        required.append({"type": "HELICOPTER", "count": 1, "reason": "Blocked roads"})
        reasoning.append("Blocked roads → helicopter option and alternate ground routes.")
    if shelter_occupancy >= 0.7 and population_affected >= 1000:
        required.append({"type": "FOOD_UNIT", "count": 1, "reason": "Shelter pressure"})
        reasoning.append("High population with shelter shortage → additional food/shelter capacity.")
    if flood in {"moderate", "high", "critical", "medium"}:
        required.append({"type": "WATER_TANKER", "count": 1, "reason": "Water / sanitation"})
        reasoning.append("Flood conditions → water tanker for potable supply.")
    if not required:
        required.append({"type": "RESCUE_TEAM", "count": 1, "reason": "Baseline watch"})
        reasoning.append("No high-severity triggers; keep a rescue team on standby.")

    merged: dict[str, dict] = {}
    for item in required:
        cur = merged.get(item["type"], {"type": item["type"], "count": 0, "reason": item["reason"]})
        cur["count"] += item["count"]
        merged[item["type"]] = cur

    warnings = []
    if roads in {"blocked", "destroyed"}:
        warnings.append("Primary road blocked — use alternate route planning (demo graph, not Google Maps).")
    if shelter_occupancy >= 0.85:
        warnings.append("Shelter near capacity — identify overflow sites.")

    return {
        "required": list(merged.values()),
        "reasoning": reasoning,
        "warnings": warnings,
        "estimate_label": ESTIMATE_LABEL,
    }
