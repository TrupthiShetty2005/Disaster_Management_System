from datetime import datetime
from typing import Protocol

from pydantic import BaseModel, Field


class WeatherSnapshot(BaseModel):
    location_id: str
    source: str
    temperature_c: float
    humidity: float
    rainfall_mm: float | None = None
    wind_speed_ms: float
    pressure_hpa: float
    visibility_km: float | None = None
    river_level_m: float | None = None
    storm_probability: float | None = None
    conditions: str
    observed_at: datetime
    provider_live: bool = False
    id: str = "snapshot"
    aoi_name: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    record_kind: str = "current_observation"
    units: dict = Field(default_factory=lambda: {
        "temperature_c": "°C",
        "humidity": "%",
        "rainfall_mm": "mm (OpenWeather 1h or 3h window, not daily)",
        "wind_speed_ms": "m/s",
        "pressure_hpa": "hPa",
        "visibility_km": "km",
    })


class ForecastPeriod(BaseModel):
    location_id: str
    source: str
    period_start: datetime
    period_end: datetime
    temperature_c: float
    rainfall_mm: float | None = None
    wind_speed_ms: float
    humidity: float | None = None
    pressure_hpa: float | None = None
    conditions: str
    id: str = "period"
    record_kind: str = "forecast"
    units: dict = Field(default_factory=lambda: {
        "temperature_c": "°C",
        "rainfall_mm": "mm (3-hour forecast period)",
        "wind_speed_ms": "m/s",
        "humidity": "%",
        "pressure_hpa": "hPa",
    })


class HistoryPoint(BaseModel):
    observed_at: datetime
    rainfall_mm: float | None = None
    temperature_c: float | None = None
    humidity: float | None = None
    wind_speed_ms: float | None = None
    river_level_m: float | None = None
    source: str
    record_kind: str = "historical_daily"
    spatial_resolution: str = "NASA POWER ~0.5° grid point (not a station gauge)"
    missing_fields: list[str] = Field(default_factory=list)
    units: dict = Field(default_factory=lambda: {
        "rainfall_mm": "mm/day (PRECTOTCORR)",
        "temperature_c": "°C (T2M)",
        "humidity": "% (RH2M)",
        "wind_speed_ms": "m/s (WS2M)",
    })


class ProviderAlert(BaseModel):
    title: str
    severity: str
    category: str
    message: str
    issued_at: datetime
    location_name: str = ""


class WeatherProvider(Protocol):
    name: str
    live: bool

    def current(self, location_id: str | None) -> WeatherSnapshot: ...

    def forecast(self, location_id: str | None) -> list[ForecastPeriod]: ...

    def history(self, location_id: str | None) -> list[HistoryPoint]: ...

    def alerts(self, location_id: str | None) -> list[ProviderAlert]: ...
