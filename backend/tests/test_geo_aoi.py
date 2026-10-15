from app.services.geo.aoi import apply_point_aoi, get_aoi, reset_aoi_to_default, set_aoi


def test_default_aoi_is_karnataka_not_kerala():
    aoi = reset_aoi_to_default()
    assert aoi["country"] == "India"
    assert aoi["state"] == "Karnataka"
    assert aoi["latitude"] > 11.5
    assert aoi["longitude"] > 74.0
    assert abs(aoi["latitude"] - 9.517) > 0.5


def test_rejects_kerala_demo_coordinates():
    reset_aoi_to_default()
    try:
        set_aoi({"latitude": 9.517, "longitude": 76.522})
        assert False, "expected reject"
    except ValueError:
        pass


def test_apply_point_aoi_uses_selected_coords():
    aoi = apply_point_aoi(15.3173, 75.7139, pad=0.1, name="Dharwad point")
    assert abs(aoi["latitude"] - 15.3173) < 1e-6
    assert abs(aoi["longitude"] - 75.7139) < 1e-6
    assert aoi["bbox"][0] < aoi["longitude"] < aoi["bbox"][2]
    got = get_aoi()
    assert got["latitude"] == aoi["latitude"]


def test_aoi_endpoints(client):
    res = client.get("/api/v1/gis/aoi")
    assert res.status_code == 200
    body = res.json()
    assert body["state"] == "Karnataka"
    missing = client.put("/api/v1/gis/aoi", json={})
    assert missing.status_code == 503
    point = client.put("/api/v1/gis/aoi", json={"latitude": 12.91, "longitude": 77.59, "aoi_name": "Bengaluru point"})
    assert point.status_code == 200
    assert abs(point.json()["latitude"] - 12.91) < 0.01
    kerala = client.put("/api/v1/gis/aoi", json={"latitude": 9.517, "longitude": 76.522})
    assert kerala.status_code == 503
    reset_aoi_to_default()
