"""Canonical demo incident — all modules should reference these IDs."""

from app.db.seed import DIS_FLOOD, LOC_KUTTANAD

DEMO_INCIDENT_ID = DIS_FLOOD
DEMO_LOCATION_ID = LOC_KUTTANAD
DEMO_REGION = "Kuttanad Wetlands (demo)"
DEMO_FLOOD_RISK_PCT = 82.0
DEMO_FLOODED_KM2 = 34.5
DEMO_AFFECTED_POPULATION = 42000
DEMO_DAMAGED_BUILDINGS = 18
DEMO_BLOCKED_ROADS = 3
DEMO_DATA_CLASS = "SIMULATED"

DEMO_FLOOD_FACTORS = [
    {"name": "Rainfall", "level": "HIGH", "value": 82.0},
    {"name": "River level", "level": "HIGH", "value": 78.0},
    {"name": "Historical flood frequency", "level": "MEDIUM", "value": 55.0},
    {"name": "Forecast trend", "level": "HIGH", "value": 80.0},
]
DEMO_NARRATIVE = [
    "Severe rainfall over Kuttanad polders (demo weather observation).",
    "Flood risk engine raises a prototype high-risk score for Polder A.",
    "High-risk zone is shown on the GIS command map.",
    "Satellite before/after comparison estimates flood expansion.",
    "Flood detection marks inundated extent and blocked roads.",
    "Damage assessment classifies buildings and road accessibility.",
    "Affected population and rescue priorities are scored.",
    "Resource recommendations (boats, medical, food) are proposed.",
    "Alert engine posts dashboard watches/warnings (not official warnings).",
    "Command dashboard and incident page refresh from the same incident ID.",
]
