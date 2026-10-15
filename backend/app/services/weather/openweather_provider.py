"""OpenWeatherMap adapter for current conditions and forecast (metric units)."""

from datetime import datetime, timedelta, timezone

import httpx

from app.core.config import settings
from app.core.providers import ProviderUnavailableError
from app.services.weather.models import ForecastPeriod, HistoryPoint, ProviderAlert, WeatherSnapshot


def _aoi_context() -> dict:
    from app.services.geo.aoi import get_aoi
    from app.services.satellite.copernicus_provider import assert_not_kerala_bbox

    aoi = get_aoi()
    lat, lon = float(aoi["latitude"]), float(aoi["longitude"])
    pad = 0.02
    assert_not_kerala_bbox([lon - pad, lat - pad, lon + pad, lat + pad])
    return aoi


class OpenWeatherProvider:
    name = "openweather"
    live = True

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.openweather_api_key
        self.query = settings.openweather_query

    def _get(self, url: str, params: dict) -> dict:
        if not self.api_key:
            raise ProviderUnavailableError(
                self.name,
                "OPENWEATHER_API_KEY not set. Current conditions and forecast unavailable.",
            )
        try:
            response = httpx.get(
                url,
                params={**params, "appid": self.api_key, "units": "metric"},
                timeout=12.0,
            )
        except httpx.HTTPError as exc:
            raise ProviderUnavailableError(self.name, f"Request failed: {exc}") from exc
        if response.status_code != 200:
            raise ProviderUnavailableError(
                self.name, f"HTTP {response.status_code}: {response.text[:200]}"
            )
        return response.json()

    def _coord_params(self) -> dict:
        aoi = _aoi_context()
        return {"lat": aoi["latitude"], "lon": aoi["longitude"]}

    def current_live(self, location_id: str | None) -> WeatherSnapshot:
        aoi = _aoi_context()
        data = self._get(
            "https://api.openweathermap.org/data/2.5/weather",
            {"lat": aoi["latitude"], "lon": aoi["longitude"]},
        )
        main = data.get("main") or {}
        if "temp" not in main:
            raise ProviderUnavailableError(self.name, "Current observation missing temperature.")
        wind = data.get("wind") or {}
        weather = (data.get("weather") or [{}])[0]
        rain_obj = data.get("rain") or {}
        # OpenWeather omits `rain` when none fell in the window — that is 0 mm, not a missing daily total.
        if "1h" in rain_obj:
            rain = float(rain_obj["1h"])
            rain_window = "1h"
        elif "3h" in rain_obj:
            rain = float(rain_obj["3h"])
            rain_window = "3h"
        else:
            rain = 0.0
            rain_window = "none_reported_treated_as_0_for_window"
        vis = data.get("visibility")
        dt = data.get("dt")
        observed = datetime.fromtimestamp(int(dt), tz=timezone.utc) if dt else datetime.now(timezone.utc)
        return WeatherSnapshot(
            id="ow-current",
            location_id=location_id or str(aoi.get("aoi_name") or "karnataka-aoi"),
            source="openweather",
            temperature_c=float(main["temp"]),
            humidity=float(main.get("humidity") or 0),
            rainfall_mm=rain,
            wind_speed_ms=float(wind.get("speed") or 0),
            pressure_hpa=float(main.get("pressure") or 0),
            visibility_km=(float(vis) / 1000.0) if vis is not None else None,
            river_level_m=None,
            storm_probability=None,
            conditions=str(weather.get("description") or "unknown"),
            observed_at=observed,
            provider_live=True,
            aoi_name=str(aoi.get("aoi_name") or ""),
            latitude=float(aoi["latitude"]),
            longitude=float(aoi["longitude"]),
            record_kind="current_observation",
            units={
                "temperature_c": "°C",
                "humidity": "%",
                "rainfall_mm": f"mm ({rain_window} window)",
                "wind_speed_ms": "m/s",
                "pressure_hpa": "hPa",
                "visibility_km": "km",
            },
        )

    def forecast_live(self, location_id: str | None) -> list[ForecastPeriod]:
        aoi = _aoi_context()
        data = self._get(
            "https://api.openweathermap.org/data/2.5/forecast",
            {"lat": aoi["latitude"], "lon": aoi["longitude"]},
        )
        items: list[ForecastPeriod] = []
        lid = location_id or str(aoi.get("aoi_name") or "karnataka-aoi")
        for row in (data.get("list") or [])[:8]:
            main = row.get("main") or {}
            if "temp" not in main or not row.get("dt"):
                continue
            wind = row.get("wind") or {}
            weather = (row.get("weather") or [{}])[0]
            start = datetime.fromtimestamp(int(row["dt"]), tz=timezone.utc)
            rain_obj = row.get("rain") or {}
            rain = float(rain_obj["3h"]) if "3h" in rain_obj else (0.0 if rain_obj == {} else None)
            items.append(
                ForecastPeriod(
                    id=f"ow-{row.get('dt')}",
                    location_id=lid,
                    source="openweather",
                    period_start=start,
                    period_end=start + timedelta(hours=3),
                    temperature_c=float(main["temp"]),
                    rainfall_mm=rain,
                    wind_speed_ms=float(wind.get("speed") or 0),
                    humidity=float(main["humidity"]) if "humidity" in main else None,
                    pressure_hpa=float(main["pressure"]) if "pressure" in main else None,
                    conditions=str(weather.get("description") or ""),
                    record_kind="forecast",
                )
            )
        if not items:
            raise ProviderUnavailableError(self.name, "Forecast list empty.")
        return items

    def current(self, location_id: str | None) -> WeatherSnapshot:
        return self.current_live(location_id)

    def forecast(self, location_id: str | None) -> list[ForecastPeriod]:
        return self.forecast_live(location_id)

    def history(self, location_id: str | None) -> list[HistoryPoint]:
        raise ProviderUnavailableError(
            self.name,
            "OpenWeather 2.5 weather/forecast is not used for daily history. NASA POWER provides historical daily fields.",
        )

    def alerts(self, location_id: str | None) -> list[ProviderAlert]:
        return []
