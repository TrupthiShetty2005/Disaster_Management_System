from datetime import datetime, timedelta, timezone

from app.services.weather.models import (
    ForecastPeriod,
    HistoryPoint,
    ProviderAlert,
    WeatherSnapshot,
)

LOC = "11111111-1111-4111-8111-111111111111"
NOW = datetime(2026, 7, 14, 6, 0, tzinfo=timezone.utc)


class MockWeatherProvider:
    name = "mock"
    live = False

    def current(self, location_id: str | None) -> WeatherSnapshot:
        lid = location_id or LOC
        return WeatherSnapshot(
            id="mock-current",
            location_id=lid,
            source="mock",
            temperature_c=27.4,
            humidity=94.0,
            rainfall_mm=48.2,
            wind_speed_ms=6.1,
            pressure_hpa=1004.0,
            visibility_km=4.2,
            river_level_m=3.1,
            storm_probability=0.34,
            conditions="Heavy rain",
            observed_at=NOW,
            provider_live=False,
        )

    def forecast(self, location_id: str | None) -> list[ForecastPeriod]:
        lid = location_id or LOC
        items: list[ForecastPeriod] = []
        for i in range(5):
            items.append(
                ForecastPeriod(
                    id=f"mock-fc-{i}",
                    location_id=lid,
                    source="mock",
                    period_start=NOW + timedelta(hours=i * 6),
                    period_end=NOW + timedelta(hours=(i + 1) * 6),
                    temperature_c=26.0 + i * 0.3,
                    rainfall_mm=max(2.0, 14.0 - i * 2.5),
                    wind_speed_ms=5.0 + i * 0.8,
                    humidity=90 - i,
                    pressure_hpa=1004 - i * 0.6,
                    conditions="Rain" if i < 3 else "Showers",
                )
            )
        return items

    def history(self, location_id: str | None) -> list[HistoryPoint]:
        series = [6.0, 9.0, 14.0, 22.0, 31.0, 41.0, 48.2]
        levels = [1.6, 1.8, 2.1, 2.4, 2.7, 2.9, 3.1]
        points: list[HistoryPoint] = []
        for i, rain in enumerate(series):
            points.append(
                HistoryPoint(
                    observed_at=NOW - timedelta(days=len(series) - 1 - i),
                    rainfall_mm=rain,
                    temperature_c=28 - i * 0.2,
                    humidity=80 + i,
                    wind_speed_ms=3.5 + i * 0.3,
                    river_level_m=levels[i],
                    source="mock",
                )
            )
        return points

    def alerts(self, location_id: str | None) -> list[ProviderAlert]:
        return [
            ProviderAlert(
                title="Heavy rainfall watch (provider)",
                severity="warning",
                category="weather",
                message="Demo meteorological watch. Not an IMD product.",
                issued_at=NOW - timedelta(hours=1),
                location_name="Kuttanad Wetlands (demo)",
            )
        ]
