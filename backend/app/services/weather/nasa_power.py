"""NASA POWER daily meteorology — point API, no key required.

Supported here: PRECTOTCORR (mm/day), T2M (°C), RH2M (%), WS2M (m/s).
Spatial resolution is the POWER ~0.5° grid (not a rain-gauge or river station).
Daily series only — not current conditions, not a forecast, not real-time.
Fill value -999 is treated as missing, never as 0 mm of rain.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import httpx

from app.core.config import settings
from app.core.providers import ProviderUnavailableError
from app.services.weather.models import HistoryPoint

POWER_FILL = -999.0
POWER_PARAMS = "PRECTOTCORR,T2M,RH2M,WS2M"


def _parse_day(day: str) -> datetime:
    return datetime.strptime(day, "%Y%m%d").replace(tzinfo=timezone.utc)


def power_value(raw) -> float | None:
    if raw is None:
        return None
    try:
        val = float(raw)
    except (TypeError, ValueError):
        return None
    if val <= -900:
        return None
    return val


class NasaPowerClient:
    name = "nasa-power"
    live = True

    def __init__(self, base_url: str | None = None):
        self.base_url = base_url or settings.nasa_power_base_url

    def fetch_daily(
        self,
        latitude: float,
        longitude: float,
        *,
        days: int = 14,
        end: datetime | None = None,
    ) -> list[HistoryPoint]:
        if not settings.nasa_power_enabled:
            raise ProviderUnavailableError(self.name, "NASA_POWER_ENABLED=false. Historical daily series unavailable.")
        end_dt = end or datetime.now(timezone.utc) - timedelta(days=1)
        start_dt = end_dt - timedelta(days=max(days - 1, 0))
        params = {
            "parameters": POWER_PARAMS,
            "community": "RE",
            "longitude": longitude,
            "latitude": latitude,
            "start": start_dt.strftime("%Y%m%d"),
            "end": end_dt.strftime("%Y%m%d"),
            "format": "JSON",
        }
        try:
            response = httpx.get(self.base_url, params=params, timeout=45.0)
        except httpx.HTTPError as exc:
            raise ProviderUnavailableError(self.name, f"Network error: {exc}") from exc
        if response.status_code != 200:
            raise ProviderUnavailableError(
                self.name, f"HTTP {response.status_code}: {response.text[:200]}"
            )
        payload = response.json()
        parameters = (payload.get("properties") or {}).get("parameter") or {}
        rain = parameters.get("PRECTOTCORR") or {}
        temp = parameters.get("T2M") or {}
        rh = parameters.get("RH2M") or {}
        wind = parameters.get("WS2M") or {}
        if not rain and not temp:
            raise ProviderUnavailableError(self.name, "Empty parameter series in NASA POWER response.")

        points: list[HistoryPoint] = []
        for day in sorted(set(rain) | set(temp) | set(rh) | set(wind)):
            r = power_value(rain.get(day))
            t = power_value(temp.get(day))
            h = power_value(rh.get(day))
            w = power_value(wind.get(day))
            missing = []
            if r is None:
                missing.append("rainfall_mm")
            if t is None:
                missing.append("temperature_c")
            if h is None:
                missing.append("humidity")
            if w is None:
                missing.append("wind_speed_ms")
            missing.append("river_level_m")
            if t is None and r is None:
                continue
            points.append(
                HistoryPoint(
                    observed_at=_parse_day(day),
                    rainfall_mm=None if r is None else round(r, 2),
                    temperature_c=None if t is None else round(t, 2),
                    humidity=None if h is None else round(h, 1),
                    wind_speed_ms=None if w is None else round(w, 2),
                    river_level_m=None,
                    source="nasa-power",
                    record_kind="historical_daily",
                    spatial_resolution="NASA POWER ~0.5° grid point (not a station gauge)",
                    missing_fields=missing,
                )
            )
        if not points:
            raise ProviderUnavailableError(self.name, "No valid daily NASA POWER points (fill values excluded).")
        return points

    def history_for_aoi(self, location_id: str | None, days: int = 14) -> list[HistoryPoint]:
        from app.services.geo.aoi import get_aoi
        from app.services.satellite.copernicus_provider import assert_not_kerala_bbox

        aoi = get_aoi()
        lat, lon = float(aoi["latitude"]), float(aoi["longitude"])
        pad = 0.02
        assert_not_kerala_bbox([lon - pad, lat - pad, lon + pad, lat + pad])
        return self.fetch_daily(lat, lon, days=days)

    def history_for_demo_aoi(self, location_id: str | None, days: int = 14) -> list[HistoryPoint]:
        return self.history_for_aoi(location_id, days=days)
