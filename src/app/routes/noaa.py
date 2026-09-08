from fastapi import APIRouter

from src.app.services.noaa_services import (
    fetch_active_alerts,
    fetch_current_observation,
    fetch_forecast,
    fetch_hourly_forecast,
    fetch_points,
    fetch_recent_alerts,
)

router = APIRouter(
    prefix="/noaa",
    tags=["NOAA"],
)


@router.get("/points")
def points(lat: float, lon: float):
    return fetch_points(lat, lon)


@router.get("/forecast")
def forecast(lat: float, lon: float):
    return fetch_forecast(lat, lon)


@router.get("/hourly-forecast")
def hourly_forecast(lat: float, lon: float):
    return fetch_hourly_forecast(lat, lon)


@router.get("/alerts/active")
def active_alerts(area: str | None = None, lat: float | None = None, lon: float | None = None):
    return fetch_active_alerts(area=area, lat=lat, lon=lon)


@router.get("/alerts/recent")
def recent_alerts(area: str | None = None):
    return fetch_recent_alerts(area=area)


@router.get("/current")
def current_observation(lat: float, lon: float):
    return fetch_current_observation(lat, lon)
