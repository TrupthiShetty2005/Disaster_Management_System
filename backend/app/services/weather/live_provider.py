"""Composite live weather: OpenWeather (current/forecast) + NASA POWER (history) + optional IMD."""

from __future__ import annotations

from app.core.config import settings
from app.core.providers import ProviderUnavailableError
from app.services.weather.imd_client import ImdClient
from app.services.weather.models import ForecastPeriod, HistoryPoint, ProviderAlert, WeatherSnapshot
from app.services.weather.nasa_power import NasaPowerClient
from app.services.weather.openweather_provider import OpenWeatherProvider


class LiveWeatherProvider:
    """Real external weather only. Does not fall back to mock numbers."""

    name = "live-composite"
    live = True

    def __init__(self) -> None:
        self.openweather = OpenWeatherProvider(settings.openweather_api_key)
        self.nasa = NasaPowerClient()
        self.imd = ImdClient()

    def current(self, location_id: str | None) -> WeatherSnapshot:
        if not settings.openweather_api_key:
            raise ProviderUnavailableError(
                "openweather",
                "OPENWEATHER_API_KEY not set. Live current weather unavailable.",
            )
        snap = self.openweather.current_live(location_id)
        return snap.model_copy(update={"river_level_m": None, "storm_probability": None})

    def forecast(self, location_id: str | None) -> list[ForecastPeriod]:
        if not settings.openweather_api_key:
            raise ProviderUnavailableError(
                "openweather",
                "OPENWEATHER_API_KEY not set. Live forecast unavailable.",
            )
        return self.openweather.forecast_live(location_id)

    def history(self, location_id: str | None) -> list[HistoryPoint]:
        return self.nasa.history_for_aoi(location_id, days=14)

    def alerts(self, location_id: str | None) -> list[ProviderAlert]:
        """Official IMD warnings only when the IMD API is configured and reachable.

        Unconfigured or failed IMD must never look like an empty all-clear.
        An empty list is returned only after a successful IMD response with zero warnings.
        """
        if not self.imd.configured:
            raise ProviderUnavailableError(
                "imd",
                "NOT_CONFIGURED: IMD_API_KEY not set. Official IMD warnings unavailable "
                "(empty list is not an all-clear).",
            )
        return self.imd.district_warnings()

    def imd_status(self) -> dict:
        return self.imd.status()
