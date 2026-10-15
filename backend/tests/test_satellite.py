from app.services.satellite.mock_provider import SAT_FLOOD_AFTER, SAT_FLOOD_BEFORE
from app.services.satellite.processing import (
    compare_scenes,
    detect_water,
    generate_demo_raster,
    mask_to_geojson,
    mask_ratio,
    preprocess,
)


def test_raster_preprocessing_preserves_shape():
    rgb = generate_demo_raster("flood", size=32)
    out = preprocess(rgb)
    assert out.shape == rgb.shape


def test_water_detection_and_area():
    flood = generate_demo_raster("flood", 32)
    dry = generate_demo_raster("normal", 32)
    assert mask_ratio(detect_water(flood)) > mask_ratio(detect_water(dry))


def test_geojson_generation():
    mask = detect_water(generate_demo_raster("flood", 24))
    geo = mask_to_geojson(mask, None, "flood")
    assert geo["type"] == "FeatureCollection"
    assert geo["features"]
    assert geo["features"][0]["geometry"]["type"] == "Polygon"


def test_comparison_logic():
    before = generate_demo_raster("flood_before", 32)
    after = generate_demo_raster("flood", 32)
    result = compare_scenes(before, after, None)
    assert result["metrics"]["flood_expansion_fraction"] >= 0
    assert "features" in result["geojson"]


def test_satellite_api(client):
    listed = client.get("/api/v1/satellite/images")
    assert listed.status_code == 200
    items = listed.json()["items"]
    assert len(items) >= 5
    image_id = next(i["id"] for i in items if i["id"] == SAT_FLOOD_AFTER)
    one = client.get(f"/api/v1/satellite/images/{image_id}")
    assert one.status_code == 200
    preview = client.get(f"/api/v1/satellite/images/{image_id}/preview")
    assert preview.status_code == 200
    analyzed = client.post(
        "/api/v1/satellite/analyze",
        json={"image_id": image_id, "analysis_type": "flood"},
    )
    assert analyzed.status_code == 200
    aid = analyzed.json()["id"]
    fetched = client.get(f"/api/v1/satellite/analysis/{aid}")
    assert fetched.status_code == 200
    assert fetched.json()["metrics"]["flooded_area_km2"] >= 0
    compared = client.post(
        "/api/v1/satellite/compare",
        json={"before_image": SAT_FLOOD_BEFORE, "after_image": SAT_FLOOD_AFTER},
    )
    assert compared.status_code == 200
    assert compared.json()["analysis_type"] == "comparison"
