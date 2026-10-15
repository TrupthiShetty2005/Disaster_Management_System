from collections import Counter

ACTIONS = {
    "person": "Account for civilians; assign ground team for welfare check.",
    "rescue_person": "Coordinate with rescue team; confirm PPE and comms.",
    "vehicle": "Keep traffic corridors clear for emergency vehicles.",
    "bus": "Check occupancy; stage evacuation transport if needed.",
    "truck": "Identify cargo hazard; restrict approach if unknown.",
    "building": "Assess occupancy; do not enter without structural check.",
    "damaged_building": "Mark unsafe; keep public 50 m back pending engineer.",
    "road": "Monitor access; share status with traffic control.",
    "blocked_road": "Reroute ambulances; request debris/boat alternative.",
    "bridge": "Limit axle load until inspection.",
    "flooded_vehicle": "Check for trapped occupants; do not approach fast water.",
    "fire": "Notify fire service; upwind staging only.",
}


def incident_summary(detections: list[dict]) -> dict:
    counts = Counter(d["label"] for d in detections)
    lines = [f"{n} {label.replace('_', ' ')} detected" for label, n in sorted(counts.items())]
    actions = []
    for label in counts:
        if label in ACTIONS:
            actions.append(ACTIONS[label])
    if not actions:
        actions.append("Continue observation; no high-priority objects.")
    return {
        "counts": dict(counts),
        "headline": "; ".join(lines) if lines else "No detections",
        "recommended_actions": actions[:6],
    }
