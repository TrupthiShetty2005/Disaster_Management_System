from app.services.satellite.processing import detect_water, detect_water_sentinel_rgb, generate_demo_raster, mask_ratio
from app.services.flood.geo import classify_flood_risk, extract_polygons, flooded_area_km2, heatmap_geojson
from app.services.flood.models import DemoFloodModel, SentinelRgbFloodModel, UNetModel
from app.services.damage.classify import classify_building, classify_road
from app.services.satellite.processing import compare_scenes


def test_demo_segmentation_is_not_claimed_trained():
    model = DemoFloodModel()
    rgb = generate_demo_raster("flood", 32)
    mask, note = model.segment(rgb)
    assert mask.shape[:2] == rgb.shape[:2]
    assert "not a trained" in note.lower()
    assert mask_ratio(mask) > 0


def test_sentinel_rgb_heuristic_labels_and_detects_water():
    model = SentinelRgbFloodModel()
    rgb = generate_demo_raster("flood", 48)
    mask, note = model.segment(rgb)
    assert mask.shape[:2] == rgb.shape[:2]
    assert "satellite-derived flood/water indication" in note.lower()
    assert "not a trained" in note.lower()
    assert mask_ratio(mask) > 0
    # Direct detector path should also return water on the synthetic flood raster.
    assert mask_ratio(detect_water_sentinel_rgb(rgb)) > 0


def test_water_change_detects_new_water_not_only_absolute():
    from app.services.satellite.processing import compare_water_change

    before = generate_demo_raster("flood_before", 48)
    after = generate_demo_raster("flood", 48)
    # Synthetic demo rasters use the demo blue-channel detector; Sentinel heuristic is for real previews.
    result = compare_water_change(before, after, None, use_sentinel_heuristic=False)
    m = result["metrics"]
    assert m["after_water_area_km2"] >= m["before_water_area_km2"]
    assert m["newly_flooded_area_km2"] > 0
    assert result["newly_flooded_geojson"]["features"]
    assert "newly" in result["newly_flooded_geojson"]["features"][0]["properties"]["name"].lower()
    assert "requires validation" in m["label"].lower()


def test_unet_not_implemented():
    try:
        UNetModel().segment(generate_demo_raster("flood", 8))
        assert False, "expected NotImplementedError"
    except NotImplementedError:
        pass


def test_polygon_extraction_and_area():
    mask = detect_water(generate_demo_raster("flood", 48))
    geo = extract_polygons(mask, None)
    assert geo["type"] == "FeatureCollection"
    assert geo["features"]
    assert flooded_area_km2(mask, None) > 0
    heat = heatmap_geojson(mask, None, cells=4)
    assert heat["features"]
    assert classify_flood_risk(10) == "low"
    assert classify_flood_risk(80) == "critical"


def test_damage_classification_and_comparison():
    before = generate_demo_raster("flood_before", 32)
    after = generate_demo_raster("flood", 32)
    result = compare_scenes(before, after, None)
    m = result["metrics"]
    b = classify_building(m["flood_expansion_fraction"], m["urban_change_fraction"], m["vegetation_loss_fraction"])
    r = classify_road(m["flood_expansion_fraction"], m["urban_change_fraction"])
    assert b in {"NO DAMAGE", "MINOR", "MODERATE", "SEVERE", "DESTROYED"}
    assert r in {"OPEN", "PARTIALLY BLOCKED", "BLOCKED", "DESTROYED"}
    assert m["flood_expansion_fraction"] >= 0


def test_flood_and_damage_api(client):
    flood = client.post("/api/v1/flood/analyze", json={"scene_kind": "flood"})
    assert flood.status_code == 200
    body = flood.json()
    assert "flooded_area" in body
    assert "flood_percentage" in body
    assert "boundary_geojson" in body
    assert "not a trained" in body["notes"].lower()
    eid = body["id"]
    listed = client.get("/api/v1/flood/events")
    assert listed.status_code == 200
    assert listed.json()["total"] >= 1
    one = client.get(f"/api/v1/flood/events/{eid}")
    assert one.status_code == 200

    dmg = client.post("/api/v1/damage/analyze", json={"before_kind": "flood_before", "after_kind": "flood"})
    assert dmg.status_code == 200
    report = dmg.json()["report"]
    assert "executive_summary" in report
    assert "building_statistics" in report
    assert "road_statistics" in report
    aid = dmg.json()["id"]
    alist = client.get("/api/v1/damage/assessments")
    assert alist.status_code == 200
    got = client.get(f"/api/v1/damage/assessments/{aid}")
    assert got.status_code == 200
    assert got.json()["pdf_available"] is False
