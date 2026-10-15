"""Demo graph routing. No Google Maps / commercial routing APIs."""

from __future__ import annotations

import heapq
from typing import Any

# Nodes around Kuttanad demo geography
NODES: dict[str, tuple[float, float]] = {
    "incident": (76.527, 9.522),
    "junction_west": (76.515, 9.518),
    "junction_east": (76.538, 9.516),
    "boat_base": (76.525, 9.519),
    "amb_base": (76.535, 9.510),
    "shelter": (76.540, 9.508),
    "hospital": (76.548, 9.512),
    "bypass": (76.520, 9.505),
}

# (from, to, distance_km, risk 0-1, blockage 0-1, accessibility)
EDGES: list[tuple[str, str, float, float, float, str]] = [
    ("incident", "junction_west", 1.4, 0.7, 0.8, "blocked"),
    ("incident", "junction_east", 1.6, 0.4, 0.1, "open"),
    ("incident", "boat_base", 0.5, 0.5, 0.0, "open"),
    ("junction_west", "bypass", 1.2, 0.3, 0.0, "open"),
    ("bypass", "shelter", 1.8, 0.25, 0.0, "open"),
    ("bypass", "amb_base", 1.5, 0.2, 0.0, "open"),
    ("junction_east", "amb_base", 0.9, 0.35, 0.15, "open"),
    ("junction_east", "hospital", 1.1, 0.2, 0.0, "open"),
    ("amb_base", "hospital", 1.4, 0.15, 0.0, "open"),
    ("amb_base", "shelter", 0.6, 0.2, 0.05, "open"),
    ("shelter", "hospital", 1.0, 0.1, 0.0, "open"),
    ("boat_base", "junction_east", 1.3, 0.45, 0.2, "open"),
]


def _undirected() -> dict[str, list[tuple[str, float, float, float, str]]]:
    g: dict[str, list[tuple[str, float, float, float, str]]] = {n: [] for n in NODES}
    for a, b, dist, risk, block, acc in EDGES:
        g[a].append((b, dist, risk, block, acc))
        g[b].append((a, dist, risk, block, acc))
    return g


def edge_cost(distance: float, risk: float, blockage: float, accessibility: str, avoid_blocked: bool) -> float | None:
    if avoid_blocked and accessibility in {"blocked", "destroyed"}:
        return None
    return distance * (1.0 + risk) * (1.0 + 3.0 * blockage)


def shortest_path(start: str, goal: str, *, safer: bool = True) -> dict[str, Any]:
    graph = _undirected()
    dist: dict[str, float] = {start: 0.0}
    prev: dict[str, str | None] = {start: None}
    heap = [(0.0, start)]
    while heap:
        cost, node = heapq.heappop(heap)
        if node == goal:
            break
        if cost > dist.get(node, 1e9):
            continue
        for nxt, dkm, risk, block, acc in graph[node]:
            step = edge_cost(dkm, risk, block, acc, avoid_blocked=safer)
            if step is None:
                continue
            new = cost + step
            if new < dist.get(nxt, 1e9):
                dist[nxt] = new
                prev[nxt] = node
                heapq.heappush(heap, (new, nxt))
    if goal not in dist:
        return shortest_path(start, goal, safer=False) if safer else {"path": [], "score": None, "geojson": None}
    path = []
    cur: str | None = goal
    while cur:
        path.append(cur)
        cur = prev.get(cur)
    path.reverse()
    coords = [[NODES[n][0], NODES[n][1]] for n in path]
    minutes = round(dist[goal] * 8, 1)
    return {
        "path": path,
        "score": round(dist[goal], 3),
        "estimated_minutes": minutes,
        "safer": safer,
        "geojson": {
            "type": "Feature",
            "geometry": {"type": "LineString", "coordinates": coords},
            "properties": {"name": f"{start}→{goal}", "safer": safer},
        },
    }


def blocked_roads_geojson() -> dict:
    features = []
    for a, b, dist, risk, block, acc in EDGES:
        if acc != "blocked" and block < 0.5:
            continue
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "LineString", "coordinates": [list(NODES[a]), list(NODES[b])]},
                "properties": {"name": f"{a}–{b}", "accessibility": acc, "blockage": block, "distance_km": dist, "risk": risk},
            }
        )
    return {"type": "FeatureCollection", "features": features}


def plan_routes() -> dict:
    primary = shortest_path("boat_base", "incident", safer=True)
    evac = shortest_path("incident", "shelter", safer=True)
    medical = shortest_path("amb_base", "hospital", safer=True)
    alt = shortest_path("incident", "hospital", safer=True)
    return {
        "engine": "demo-graph",
        "note": "Graph-based demo routing. Not Google Maps or live traffic.",
        "primary_access": primary,
        "evacuation": evac,
        "medical": medical,
        "alternate_to_hospital": alt,
        "blocked_roads": blocked_roads_geojson(),
        "estimated_response_time_min": min(
            primary.get("estimated_minutes") or 99,
            evac.get("estimated_minutes") or 99,
        ),
    }
