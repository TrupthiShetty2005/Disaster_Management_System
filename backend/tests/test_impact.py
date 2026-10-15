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


def test_no_footprint_means_no_exposure():
    assert impact.assess(None, "flood")["status"] == "no_hazard_footprint"


def test_osm_outage_is_reported_not_guessed(monkeypatch):
    def down(_bbox):
        raise SourceUnavailable("overpass", "All Overpass mirrors failed")

    monkeypatch.setattr(impact.osm, "infrastructure", down)
    out = impact.assess(impact.hazard_from_points([[76.0, 15.0]]), "fire")
    assert out["status"] == "osm_unavailable"
    assert out["loss"] is None
