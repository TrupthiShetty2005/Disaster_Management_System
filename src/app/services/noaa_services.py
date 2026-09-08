import requests
from fastapi import HTTPException

from src.app.config.settings import NOAA_USER_AGENT

BASE_URL = "https://api.weather.gov"


def _headers():
    return {
        "User-Agent": NOAA_USER_AGENT,
        "Accept": "application/geo+json",
    }


def _require_user_agent():
    if not NOAA_USER_AGENT:
        raise HTTPException(
            status_code=500,
            detail="NOAA_USER_AGENT is not set. Add it to your .env file.",
        )


def _get_json(url: str, params: dict | None = None):
    _require_user_agent()
    response = requests.get(url, params=params, headers=_headers(), timeout=10)

    try:
        data = response.json()
    except ValueError:
        data = {}

    if response.status_code != 200:
        detail = data.get("detail") or data.get("title") or "NOAA API request failed"
        raise HTTPException(status_code=response.status_code, detail=detail)

    return data


def fetch_points(lat: float, lon: float):
    return _get_json(f"{BASE_URL}/points/{lat},{lon}")


def fetch_forecast(lat: float, lon: float):
    points = fetch_points(lat, lon)
    forecast_url = points["properties"]["forecast"]
    return _get_json(forecast_url)


def fetch_hourly_forecast(lat: float, lon: float):
    points = fetch_points(lat, lon)
    forecast_url = points["properties"]["forecastHourly"]
    return _get_json(forecast_url)


def fetch_active_alerts(area: str | None = None, lat: float | None = None, lon: float | None = None):
    params = {}

    if area:
        params["area"] = area.upper()
    elif lat is not None and lon is not None:
        params["point"] = f"{lat},{lon}"

    return _get_json(f"{BASE_URL}/alerts/active", params=params or None)


def fetch_recent_alerts(area: str | None = None):
    params = {"area": area.upper()} if area else None
    return _get_json(f"{BASE_URL}/alerts", params=params)


def fetch_current_observation(lat: float, lon: float):
    points = fetch_points(lat, lon)
    stations = _get_json(points["properties"]["observationStations"])

    features = stations.get("features", [])
    if not features:
        raise HTTPException(
            status_code=404,
            detail="No observation stations found for this location",
        )

    station_id = features[0]["properties"]["stationIdentifier"]
    data = _get_json(f"{BASE_URL}/stations/{station_id}/observations/latest")
    props = data["properties"]

    return {
        "station": props.get("station"),
        "timestamp": props.get("timestamp"),
        "temperature_c": _metric_value(props.get("temperature")),
        "wind_speed_mps": _metric_value(props.get("windSpeed")),
        "humidity_pct": _metric_value(props.get("relativeHumidity")),
        "text_description": props.get("textDescription"),
    }


def _metric_value(field: dict | None):
    if not field:
        return None
    return field.get("value")
