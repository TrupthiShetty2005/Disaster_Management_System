from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

RULES_PATH = Path(__file__).with_name("rules.json")


@lru_cache(maxsize=1)
def load_rules() -> dict[str, Any]:
    return json.loads(RULES_PATH.read_text(encoding="utf-8"))


def reload_rules() -> dict[str, Any]:
    load_rules.cache_clear()
    return load_rules()


def score_to_severity(score: float, disaster_type: str = "flood") -> str:
    rules = load_rules()
    bands = rules.get("by_type", {}).get(disaster_type) or rules["bands"]["default"]
    if score >= float(bands.get("critical", 75)):
        return "CRITICAL"
    if score >= float(bands.get("warning", 50)):
        return "WARNING"
    if score >= float(bands.get("watch", 30)):
        return "WATCH"
    return "INFO"


def recommended_action(severity: str) -> str:
    return load_rules().get("actions", {}).get(severity.upper(), "Monitor and validate.")


def disclaimer() -> str:
    return load_rules()["disclaimer"]


def dispatch_threshold(disaster_type: str) -> float:
    bands = load_rules().get("by_type", {}).get(disaster_type) or {}
    return float(bands.get("dispatch_min", 70))
