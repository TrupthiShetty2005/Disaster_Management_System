from app.core.errors import SourceUnavailable
from app.services import impact


def _infra(_bbox):
    return [
        {"type": "way", "id": 1, "tags": {"building": "yes"}, "center": {"lat": 15.0, "lon": 76.0}},
        {"type": "way", "id": 2, "tags": {"building": "house"}, "center": {"lat": 15.05, "lon": 76.05}},
        {"type": "way", "id": 3, "tags": {"highway": "primary"}, "geometry": [{"lat": 15.0, "lon": 75.98}, {"lat": 15.0, "lon": 76.02}]},
        {"type": "way", "id": 4, "tags": {"power": "line"}, "geometry": [{"lat": 14.99, "lon": 76.0}, {"lat": 15.01, "lon": 76.0}]},
        {"type": "node", "id": 5, "tags": {"amenity": "school", "name": "Govt School"}, "lat": 15.001, "lon": 76.001},
    ]


def test_fire_footprint_exposure_and_loss(monkeypatch):
    monkeypatch.setattr(impact.osm, "infrastructure", _infra)
    hazard = impact.hazard_from_points([[76.0, 15.0]], radius_m=1000)
    out = impact.assess(hazard, "fire")

    assert out["status"] == "complete"
    e = out["exposed"]
    assert e["buildings"] == 1 and e["buildings_in_search_area"] == 2
    assert 1.8 < e["major_road_km"] < 2.1  # 2 km diameter circle crossing the road through its centre
    assert 1.8 < e["power_line_km"] < 2.3
    assert e["facilities"] == {"education": 1}

    loss = out["loss"]
    assert loss["damage_ratio"] == 0.5
    assert loss["estimated_loss"] == round(loss["exposed_replacement_value"] * 0.5)
    assert "assumptions" in loss and loss["assumptions"]["building_inr"] > 0


def _square(lon, lat, half=0.0004):
    return [{"lon": lon - half, "lat": lat - half}, {"lon": lon + half, "lat": lat - half}, {"lon": lon + half, "lat": lat + half}, {"lon": lon - half, "lat": lat + half}, {"lon": lon - half, "lat": lat - half}]


def _asset_infra(_bbox):
    return [
        {"type": "way", "id": 10, "tags": {"building": "yes", "height": "12 m"}, "center": {"lat": 15.0, "lon": 76.0}},
        {"type": "way", "id": 11, "tags": {"building": "house", "building:levels": "2"}, "center": {"lat": 15.0, "lon": 76.0025}},
        {"type": "way", "id": 12, "tags": {"building": "yes"}, "center": {"lat": 15.0, "lon": 76.0096}},
        {"type": "way", "id": 13, "tags": {"building": "yes"}, "center": {"lat": 15.1, "lon": 76.1}},
        {"type": "way", "id": 20, "tags": {"highway": "primary", "name": "SH-1"}, "geometry": [{"lat": 15.0, "lon": 75.98}, {"lat": 15.0, "lon": 76.02}]},
        {"type": "node", "id": 30, "tags": {"amenity": "hospital", "name": "PHC"}, "lat": 15.001, "lon": 76.001},
    ]


def _outlines(ids):
    centers = {10: (76.0, 15.0), 11: (76.0025, 15.0), 12: (76.0096, 15.0), 13: (76.1, 15.1)}
    return {i: _square(*centers[i]) for i in ids if i in centers}


def test_asset_geojson_buildings_lines_facilities(monkeypatch):
    monkeypatch.setattr(impact.osm, "infrastructure", _asset_infra)
    requested = []
    monkeypatch.setattr(impact.osm, "building_geometries", lambda ids: requested.extend(ids) or _outlines(ids))
    hazard = impact.hazard_from_points([[76.0, 15.0]], radius_m=1000)  # ≈ 0.0093° in longitude at 15° N
    out = impact.assets(hazard, "flood")

    assert out["status"] == "complete"
    assert sorted(requested) == [10, 11, 12]  # far building 13 is neither affected nor nearby: never fetched
    b = {f["properties"]["osm_id"]: f["properties"] for f in out["buildings"]["features"]}
    assert b["way/10"]["affected"] and b["way/10"]["damage_class"] == "newly_flooded"
    assert b["way/10"]["height_m"] == 12.0 and b["way/10"]["height_source"] == "osm_height"
    assert b["way/11"]["height_m"] == 6.0 and b["way/11"]["height_source"] == "osm_levels"
    assert not b["way/12"]["affected"] and b["way/12"]["damage_class"] == "edge_contact" and 0 < b["way/12"]["overlap_pct"] < 100
    assert b["way/12"]["height_source"] == "estimated_default"
    assert out["buildings"]["features"][0]["geometry"]["type"] == "Polygon"

    s = out["summary"]
    assert s["buildings_affected"] == 2 == impact.assess(hazard, "flood")["exposed"]["buildings"]
    assert s["buildings_edge_contact"] == 1
    assert 1.8 < s["road_km_affected"] < 2.1
    lines = out["lines"]["features"]
    assert {ln["properties"]["affected"] for ln in lines} == {True, False}
    assert all(ln["properties"]["name"] == "SH-1" for ln in lines)
    fac = out["facilities"]["features"][0]["properties"]
    assert fac["kind"] == "health" and fac["affected"]
    assert "Unknown" in out["method"]["flood_depth"]


def test_asset_outline_outage_is_reported(monkeypatch):
    def down(_ids):
        raise SourceUnavailable("overpass", "All Overpass mirrors failed")

    monkeypatch.setattr(impact.osm, "infrastructure", _asset_infra)
    monkeypatch.setattr(impact.osm, "building_geometries", down)
    out = impact.assets(impact.hazard_from_points([[76.0, 15.0]], 1000), "fire")
    assert out["status"] == "osm_unavailable" and "Building outlines" in out["detail"]


def test_building_height_parsing():
    assert impact.building_height({"height": "30 ft"})["height_m"] == 9.1
    assert impact.building_height({"height": "4,5"})["height_m"] == 4.5
    assert impact.building_height({"building:levels": "3"}) == {"height_m": 9.0, "height_source": "osm_levels", "levels": 3.0}
    assert impact.building_height({"height": "abc"})["height_source"] == "estimated_default"


def test_no_footprint_means_no_exposure():
    assert impact.assess(None, "flood")["status"] == "no_hazard_footprint"


def test_osm_outage_is_reported_not_guessed(monkeypatch):
    def down(_bbox):
        raise SourceUnavailable("overpass", "All Overpass mirrors failed")

    monkeypatch.setattr(impact.osm, "infrastructure", down)
    out = impact.assess(impact.hazard_from_points([[76.0, 15.0]]), "fire")
    assert out["status"] == "osm_unavailable"
    assert out["loss"] is None
