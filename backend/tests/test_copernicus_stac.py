from datetime import date
import httpx
import pytest

from app.core.providers import ProviderUnavailableError
from app.services.satellite.copernicus_provider import (
    clear_stac_catalogue_cache,
    CopernicusStacProvider,
    SATELLITE_MIN_START,
    assert_not_kerala_bbox,
    bbox_centroid,
    bboxes_intersect,
    build_search_body,
    classify_assets,
    feature_intersects_aoi,
    is_kerala_demo_bbox,
    pick_preview_href,
    resolve_search_window,
    stac_datetime_range,
    stac_scene_bbox,
)


def test_default_window_starts_may_2026():
    start, end = resolve_search_window(None, None, today=date(2026, 10, 15))
    assert start == SATELLITE_MIN_START
    assert start == date(2026, 5, 1)
    assert end == date(2026, 10, 15)
    rng = stac_datetime_range(start, end)
    assert rng.startswith("2026-05-01")
    assert "2026-10-15" in rng


def test_invalid_dates():
    with pytest.raises(ValueError, match="cannot be before"):
        resolve_search_window(date(2025, 1, 1), date(2026, 6, 1), today=date(2026, 10, 15))
    with pytest.raises(ValueError, match="on or after"):
        resolve_search_window(date(2026, 8, 1), date(2026, 6, 1), today=date(2026, 10, 15))
    with pytest.raises(ValueError, match="future"):
        resolve_search_window(date(2026, 5, 1), date(2026, 12, 1), today=date(2026, 10, 15))


def test_kerala_geo_filter():
    kuttanad = [76.49, 9.49, 76.56, 9.55]
    bengaluru = [77.53, 12.91, 77.65, 13.03]
    assert is_kerala_demo_bbox(kuttanad)
    assert not is_kerala_demo_bbox(bengaluru)
    with pytest.raises(ProviderUnavailableError, match="Kerala"):
        assert_not_kerala_bbox(kuttanad)


def test_search_body_uses_aoi_and_dates():
    body = build_search_body(
        collections=["sentinel-2-l2a"],
        bbox=[77.53, 12.91, 77.65, 13.03],
        start_d=date(2026, 5, 1),
        end_d=date(2026, 10, 15),
        max_cloud=40,
    )
    assert body["bbox"] == [77.53, 12.91, 77.65, 13.03]
    assert "2026-05-01" in body["datetime"]
    assert "sentinel-2-l2a" in body["collections"]
    assert 76.52 not in body["bbox"]


def test_asset_classification_auth():
    assets = {
        "thumbnail": {"href": "https://cdn.example/preview.jpg", "type": "image/jpeg"},
        "product": {"href": "https://catalogue.dataspace.copernicus.eu/odata/v1/Products(1)/$value"},
    }
    classified = classify_assets(assets)
    assert classified["thumbnail"]["role"] == "preview"
    assert classified["thumbnail"]["auth_required"] is False
    assert classified["thumbnail"]["downloaded"] is False
    assert classified["product"]["auth_required"] is True
    href, auth = pick_preview_href(assets)
    assert href.endswith("preview.jpg")
    assert auth is False


class _FakeResponse:
    def __init__(self, status_code, payload=None, content=b"", text=""):
        self.status_code = status_code
        self._payload = payload or {}
        self.content = content
        self.text = text or ""

    def json(self):
        return self._payload


def _karnataka_aoi():
    return {
        "aoi_name": "Bengaluru Urban",
        "latitude": 12.9716,
        "longitude": 77.5946,
        "bbox": [77.53, 12.91, 77.65, 13.03],
        "district": "Bengaluru Urban",
    }


def test_empty_catalogue_fails_closed(monkeypatch):
    monkeypatch.setattr("app.services.geo.aoi.get_aoi", _karnataka_aoi)

    def fake_post(url, json=None, headers=None, timeout=None):
        return _FakeResponse(200, {"features": []})

    monkeypatch.setattr(httpx, "post", fake_post)
    provider = CopernicusStacProvider()
    with pytest.raises(ProviderUnavailableError, match="No Sentinel-2"):
        provider.refresh(start=date(2026, 5, 1), end=date(2026, 10, 15))


def test_network_error_fails_closed(monkeypatch):
    monkeypatch.setattr("app.services.geo.aoi.get_aoi", _karnataka_aoi)

    def boom(*args, **kwargs):
        raise httpx.ConnectError("dns")

    monkeypatch.setattr(httpx, "post", boom)
    provider = CopernicusStacProvider()
    with pytest.raises(ProviderUnavailableError, match="Network error"):
        provider.refresh(start=date(2026, 5, 1), end=date(2026, 10, 15))


def test_excessive_cloud_fails_closed(monkeypatch):
    monkeypatch.setattr("app.services.geo.aoi.get_aoi", _karnataka_aoi)

    def fake_post(url, json=None, headers=None, timeout=None):
        return _FakeResponse(
            200,
            {
                "features": [
                    {
                        "id": "S2_CLOUDY",
                        "collection": "sentinel-2-l2a",
                        "bbox": [77.53, 12.91, 77.65, 13.03],
                        "properties": {"datetime": "2026-06-01T05:00:00Z", "eo:cloud_cover": 88},
                        "assets": {},
                    }
                ]
            },
        )

    monkeypatch.setattr(httpx, "post", fake_post)
    provider = CopernicusStacProvider()
    with pytest.raises(ProviderUnavailableError, match="cloud cover"):
        provider.refresh(start=date(2026, 5, 1), end=date(2026, 10, 15), max_cloud=40)


def test_missing_preview_is_catalogue_only(monkeypatch):
    monkeypatch.setattr("app.services.geo.aoi.get_aoi", _karnataka_aoi)

    def fake_post(url, json=None, headers=None, timeout=None):
        return _FakeResponse(
            200,
            {
                "features": [
                    {
                        "id": "S2A_MSIL2A_20260601T050000_N0511",
                        "collection": "sentinel-2-l2a",
                        "bbox": [77.53, 12.91, 77.65, 13.03],
                        "properties": {
                            "datetime": "2026-06-01T05:00:00Z",
                            "eo:cloud_cover": 12,
                            "platform": "sentinel-2",
                        },
                        "assets": {
                            "product": {
                                "href": "https://catalogue.dataspace.copernicus.eu/odata/v1/Products(1)/$value"
                            }
                        },
                    }
                ]
            },
        )

    monkeypatch.setattr(httpx, "post", fake_post)
    provider = CopernicusStacProvider()
    scenes = provider.refresh(start=date(2026, 5, 1), end=date(2026, 10, 15))
    assert scenes[0].status == "catalogue_only"
    assert scenes[0].metadata["stac_id"] == "S2A_MSIL2A_20260601T050000_N0511"
    assert scenes[0].metadata["full_raster_downloaded"] is False
    with pytest.raises(ProviderUnavailableError, match="No preview"):
        provider.fetch_thumbnail_bytes(scenes[0].id)


def test_list_scenes_serves_cache_on_429(monkeypatch):
    clear_stac_catalogue_cache()
    monkeypatch.setattr("app.services.geo.aoi.get_aoi", _karnataka_aoi)
    hits = {"n": 0}

    def fake_post(url, json=None, headers=None, timeout=None):
        hits["n"] += 1
        if hits["n"] > 1:
            return _FakeResponse(429, {"error": "WAF", "message": "Rate limit exceeded", "status": 429})
        return _FakeResponse(
            200,
            {
                "features": [
                    {
                        "id": "S2A_CACHED",
                        "collection": "sentinel-2-l2a",
                        "bbox": [77.53, 12.91, 77.65, 13.03],
                        "properties": {
                            "datetime": "2026-06-01T05:00:00Z",
                            "eo:cloud_cover": 10,
                            "platform": "sentinel-2",
                        },
                        "assets": {"thumbnail": {"href": "https://cdn.example/t.jpg"}},
                    }
                ]
            },
        )

    monkeypatch.setattr(httpx, "post", fake_post)
    provider = CopernicusStacProvider()
    first = provider.list_scenes(start=date(2026, 5, 1), end=date(2026, 10, 15))
    assert first[0].metadata["stac_id"] == "S2A_CACHED"
    import app.services.satellite.copernicus_provider as copernicus_mod

    copernicus_mod._STAC_CACHE["ts"] = 0.0
    other = CopernicusStacProvider()
    second = other.list_scenes(start=date(2026, 5, 1), end=date(2026, 10, 15))
    assert second[0].metadata["stac_id"] == "S2A_CACHED"
    st = other.status()
    assert st["available"] is True
    assert st["scene_count"] >= 1
    clear_stac_catalogue_cache()


def test_thumbnail_401_reports_auth(monkeypatch):
    monkeypatch.setattr("app.services.geo.aoi.get_aoi", _karnataka_aoi)

    def fake_post(url, json=None, headers=None, timeout=None):
        return _FakeResponse(
            200,
            {
                "features": [
                    {
                        "id": "S2_PREVIEW",
                        "collection": "sentinel-2-l2a",
                        "bbox": [77.5, 12.9, 77.7, 13.1],
                        "properties": {"datetime": "2026-06-02T05:00:00Z", "eo:cloud_cover": 8},
                        "assets": {"thumbnail": {"href": "https://cdn.example/t.jpg"}},
                    }
                ]
            },
        )

    def fake_get(url, headers=None, timeout=None, follow_redirects=None):
        return _FakeResponse(401, content=b"", text="unauthorized")

    monkeypatch.setattr(httpx, "post", fake_post)
    monkeypatch.setattr(httpx, "get", fake_get)
    provider = CopernicusStacProvider()
    scenes = provider.refresh(start=date(2026, 5, 1), end=date(2026, 10, 15))
    with pytest.raises(ProviderUnavailableError, match="authentication required"):
        provider.fetch_thumbnail_bytes(scenes[0].id)


def test_kerala_bbox_rejected_on_search(monkeypatch):
    monkeypatch.setattr(
        "app.services.geo.aoi.get_aoi",
        lambda: {
            "aoi_name": "Kuttanad",
            "latitude": 9.517,
            "longitude": 76.522,
            "bbox": [76.49, 9.49, 76.56, 9.55],
        },
    )
    provider = CopernicusStacProvider()
    with pytest.raises(ProviderUnavailableError, match="Kerala"):
        provider._aoi_bbox()


def test_api_invalid_start_date(client):
    res = client.get("/api/v1/satellite/images?start=2025-01-01&end=2026-06-01")
    assert res.status_code == 400


def _dakshina_kannada_aoi():
    return {
        "aoi_name": "Dakshina Kannada, Karnataka, India",
        "latitude": 12.82,
        "longitude": 75.23,
        "bbox": [74.85, 12.45, 75.55, 13.15],
        "district": "Dakshina Kannada",
    }


def test_scene_centroid_comes_from_stac_not_default_aoi(monkeypatch):
    monkeypatch.setattr("app.services.geo.aoi.get_aoi", _dakshina_kannada_aoi)
    scene_bbox = [74.90, 12.50, 75.40, 13.00]

    def fake_post(url, json=None, headers=None, timeout=None):
        return _FakeResponse(
            200,
            {
                "features": [
                    {
                        "id": "S2A_MSIL2A_DK_TILE",
                        "collection": "sentinel-2-l2a",
                        "bbox": scene_bbox,
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [[
                                [74.90, 12.50],
                                [75.40, 12.50],
                                [75.40, 13.00],
                                [74.90, 13.00],
                                [74.90, 12.50],
                            ]],
                        },
                        "properties": {
                            "datetime": "2026-06-01T05:10:00Z",
                            "eo:cloud_cover": 11.2,
                            "platform": "sentinel-2",
                        },
                        "assets": {"thumbnail": {"href": "https://cdn.example/dk.jpg"}},
                    }
                ]
            },
        )

    monkeypatch.setattr(httpx, "post", fake_post)
    provider = CopernicusStacProvider()
    scenes = provider.refresh(start=date(2026, 5, 1), end=date(2026, 10, 15))
    scene = scenes[0]
    lon, lat = bbox_centroid(scene_bbox)
    assert scene.metadata["stac_id"] == "S2A_MSIL2A_DK_TILE"
    assert scene.acquisition_time.year == 2026
    assert abs(scene.cloud_cover - 11.2) < 1e-6
    assert abs(scene.latitude - lat) < 1e-9
    assert abs(scene.longitude - lon) < 1e-9
    assert abs(scene.latitude - 12.9716) > 0.05
    assert abs(scene.longitude - 77.5946) > 0.5
    assert abs(scene.latitude - 12.82) > 0.05 or abs(scene.longitude - 75.23) > 0.05
    assert scene.metadata["aoi_latitude"] == 12.82
    assert scene.metadata["aoi_longitude"] == 75.23
    assert scene.metadata["footprint_available"] is True
    assert scene.bounding_box["type"] == "Polygon"


def test_non_intersecting_scene_is_excluded(monkeypatch):
    monkeypatch.setattr("app.services.geo.aoi.get_aoi", _dakshina_kannada_aoi)

    def fake_post(url, json=None, headers=None, timeout=None):
        return _FakeResponse(
            200,
            {
                "features": [
                    {
                        "id": "S2_BENGALURU_ONLY",
                        "collection": "sentinel-2-l2a",
                        "bbox": [77.53, 12.91, 77.65, 13.03],
                        "properties": {"datetime": "2026-06-01T05:00:00Z", "eo:cloud_cover": 8},
                        "assets": {},
                    },
                    {
                        "id": "S2_NO_GEOMETRY",
                        "collection": "sentinel-2-l2a",
                        "properties": {"datetime": "2026-06-02T05:00:00Z", "eo:cloud_cover": 8},
                        "assets": {},
                    },
                ]
            },
        )

    monkeypatch.setattr(httpx, "post", fake_post)
    provider = CopernicusStacProvider()
    with pytest.raises(ProviderUnavailableError, match="No Sentinel-2"):
        provider.refresh(start=date(2026, 5, 1), end=date(2026, 10, 15))


def test_geometry_without_bbox_does_not_use_aoi_center():
    geom = {
        "type": "Polygon",
        "coordinates": [[[75.0, 12.7], [75.4, 12.7], [75.4, 13.0], [75.0, 13.0], [75.0, 12.7]]],
    }
    bbox = stac_scene_bbox({"geometry": geom})
    assert bbox is not None
    lon, lat = bbox_centroid(bbox)
    assert abs(lon - 77.5946) > 1
    assert abs(lat - 12.9716) > 0.05
    aoi = [74.85, 12.45, 75.55, 13.15]
    assert feature_intersects_aoi({"geometry": geom}, aoi)
    assert not feature_intersects_aoi({"geometry": geom}, [77.53, 12.91, 77.65, 13.03])
    assert not feature_intersects_aoi({"id": "bare"}, aoi)
    assert not bboxes_intersect([74.85, 12.45, 75.55, 13.15], [77.53, 12.91, 77.65, 13.03])


def test_api_date_filter_keeps_july_mock(client):
    res = client.get("/api/v1/satellite/images?start=2026-05-01&end=2026-10-15")
    assert res.status_code == 200
    assert res.json()["total"] >= 1
    assert res.json()["query"]["start"] == "2026-05-01"
    assert res.json()["query"]["live_stream"] is False
