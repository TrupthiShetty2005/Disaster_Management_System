import httpx
import pytest

from app.core.providers import ProviderUnavailableError
from app.services.gis.overpass import (
    GisService,
    classify_osm_layer,
    geometry_from_osm,
    invalidate_gis_cache,
    valid_lonlat,
)


def _karnataka_aoi():
    return {
        "aoi_name": "Bengaluru Urban",
        "latitude": 12.9716,
        "longitude": 77.5946,
        "bbox": [77.53, 12.91, 77.65, 13.03],
        "bbox_pad_deg": 0.06,
    }


class _FakeResponse:
    def __init__(self, status_code, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}
        self.text = text
        self._json_ok = payload is not None or status_code == 200

    def json(self):
        if self._payload is None:
            raise ValueError("not json")
        return self._payload


def test_geometry_validation():
    assert valid_lonlat(77.59, 12.97)
    assert not valid_lonlat(200.0, 12.97)
    assert geometry_from_osm({"lat": 12.97, "lon": 77.59, "tags": {}})["type"] == "Point"
    assert geometry_from_osm({"lat": 99.0, "lon": 77.59, "tags": {}}) is None
    line = geometry_from_osm(
        {
            "tags": {"highway": "primary"},
            "geometry": [{"lon": 77.1, "lat": 12.9}, {"lon": 77.2, "lat": 12.91}],
        }
    )
    assert line["type"] == "LineString"
    assert geometry_from_osm({"tags": {"highway": "primary"}, "geometry": [{"lon": 77.1, "lat": 12.9}]})[
        "type"
    ] == "Point"
    assert geometry_from_osm({"tags": {}, "geometry": []}) is None


def test_layer_classification():
    assert classify_osm_layer({"highway": "primary"}) == "roads"
    assert classify_osm_layer({"bridge": "yes", "highway": "primary"}) == "bridges"
    assert classify_osm_layer({"railway": "rail"}) == "railways"
    assert classify_osm_layer({"waterway": "river"}) == "waterways"
    assert classify_osm_layer({"building": "yes"}) == "buildings"
    assert classify_osm_layer({"amenity": "hospital"}) == "hospitals"
    assert classify_osm_layer({"amenity": "fire_station"}) == "fire"
    assert classify_osm_layer({"amenity": "shelter"}) == "shelters"
    assert classify_osm_layer({"shop": "bakery"}) is None


def test_empty_overpass_is_not_mock(monkeypatch):
    invalidate_gis_cache()
    monkeypatch.setattr("app.services.geo.aoi.get_aoi", _karnataka_aoi)
    monkeypatch.setattr("app.core.config.settings.use_mock_providers", False)
    monkeypatch.setattr("app.core.config.settings.gis_overpass_enabled", True)

    def fake_post(*args, **kwargs):
        return _FakeResponse(200, {"elements": []})

    monkeypatch.setattr(httpx, "post", fake_post)
    payload = GisService().fetch_features(force=True)
    assert payload["total"] == 0
    assert payload["empty_result"] is True
    assert payload["features"] == []
    assert payload["data_provenance"]["official_government_data"] is False
    assert "not a confirmed absence" in payload["data_provenance"]["limitations"].lower()
    assert payload["layer_status"]["hospitals"] == "not_mapped_in_osm_for_this_query"


def test_overpass_timeout(monkeypatch):
    invalidate_gis_cache()
    monkeypatch.setattr("app.services.geo.aoi.get_aoi", _karnataka_aoi)
    monkeypatch.setattr("app.core.config.settings.use_mock_providers", False)

    def boom(*args, **kwargs):
        raise httpx.TimeoutException("timeout")

    monkeypatch.setattr(httpx, "post", boom)
    with pytest.raises(ProviderUnavailableError, match="timed out"):
        GisService().fetch_features(force=True)


def test_overpass_rate_limit(monkeypatch):
    invalidate_gis_cache()
    monkeypatch.setattr("app.services.geo.aoi.get_aoi", _karnataka_aoi)
    monkeypatch.setattr("app.core.config.settings.use_mock_providers", False)

    def fake_post(*args, **kwargs):
        return _FakeResponse(429, {"error": "rate"})

    monkeypatch.setattr(httpx, "post", fake_post)
    with pytest.raises(ProviderUnavailableError, match="429"):
        GisService().fetch_features(force=True)


def test_skips_invalid_geometry_keeps_valid(monkeypatch):
    invalidate_gis_cache()
    monkeypatch.setattr("app.services.geo.aoi.get_aoi", _karnataka_aoi)
    monkeypatch.setattr("app.core.config.settings.use_mock_providers", False)

    def fake_post(*args, **kwargs):
        return _FakeResponse(
            200,
            {
                "elements": [
                    {"type": "node", "id": 1, "lat": 99.0, "lon": 77.59, "tags": {"amenity": "hospital"}},
                    {
                        "type": "way",
                        "id": 99,
                        "tags": {"highway": "primary", "name": "MG Road"},
                        "geometry": [{"lon": 77.59, "lat": 12.97}, {"lon": 77.60, "lat": 12.98}],
                    },
                ]
            },
        )

    monkeypatch.setattr(httpx, "post", fake_post)
    payload = GisService().fetch_features(force=True)
    assert payload["total"] == 1
    assert payload["skipped_invalid_geometry"] >= 1
    feat = payload["features"][0]
    assert feat["properties"]["osm_id"] == 99
    assert feat["geometry"]["type"] == "LineString"
    assert feat["properties"]["layer"] == "roads"


def test_kerala_bbox_rejected(monkeypatch):
    monkeypatch.setattr(
        "app.services.geo.aoi.get_aoi",
        lambda: {
            "aoi_name": "Kuttanad",
            "latitude": 9.517,
            "longitude": 76.522,
            "bbox": [76.49, 9.49, 76.56, 9.55],
        },
    )
    with pytest.raises(ProviderUnavailableError, match="Kerala"):
        GisService()
