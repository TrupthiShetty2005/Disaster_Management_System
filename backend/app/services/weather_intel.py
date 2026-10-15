from app.core.config import settings
from app.core.providers import ProviderUnavailableError
from app.services.risk.cyclone import evaluate_cyclone
from app.services.risk.flood import BaselineFloodRiskModel, FloodRiskInput, overlay_demo_flood
from app.services.risk.pipeline import (
    persist_alert_candidate,
    should_raise_cyclone_alert,
    should_raise_flood_alert,
)
from app.services.risk.rainfall import analyze_rainfall
from app.services.weather.factory import get_weather_provider
from app.services.weather.models import ForecastPeriod, HistoryPoint, WeatherSnapshot


def _wind_trend(forecast: list[ForecastPeriod]) -> float:
    if len(forecast) < 2:
        return 0.0
    return forecast[-1].wind_speed_ms - forecast[0].wind_speed_ms


class WeatherIntelService:
    def __init__(self, db=None):
        self.db = db
        self.provider = get_weather_provider()
        self.flood_model = BaselineFloodRiskModel()

    def current(self, location_id: str | None) -> WeatherSnapshot:
        return self.provider.current(location_id)

    def forecast(self, location_id: str | None) -> list[ForecastPeriod]:
        return self.provider.forecast(location_id)

    def history(self, location_id: str | None) -> list[HistoryPoint]:
        return self.provider.history(location_id)

    def rainfall(self, location_id: str | None):
        hist = self.history(location_id)
        daily = [p.rainfall_mm for p in hist]
        values = [v for v in daily if v is not None]
        if not values:
            raise ProviderUnavailableError(
                "nasa-power",
                "NASA POWER rainfall series has no valid PRECTOTCORR days (missing values not filled with 0).",
            )
        climatology = (sum(values[:-1]) / max(len(values) - 1, 1)) if len(values) >= 2 else None
        result = analyze_rainfall(daily, climatology_mm=climatology)
        source = hist[-1].source if hist else "unknown"
        label = (
            "NASA POWER daily PRECTOTCORR anomaly (heuristic index, not an official rainfall warning)"
            if source == "nasa-power"
            else ("Prototype rainfall analysis" if settings.use_mock_providers else "Rainfall analysis")
        )
        return result.__class__(
            cumulative_mm=result.cumulative_mm,
            intensity_mm_h=result.intensity_mm_h,
            anomaly=result.anomaly,
            short_term_risk=result.short_term_risk,
            label=label,
        )

    def flood(self, location_id: str | None):
        snap = None
        rain = None
        try:
            snap = self.current(location_id)
        except ProviderUnavailableError:
            snap = None
        try:
            rain = self.rainfall(location_id)
        except ProviderUnavailableError:
            rain = None
        if settings.use_mock_providers:
            if snap is None:
                snap = self.current(location_id)
            if rain is None:
                rain = self.rainfall(location_id)
            result = self.flood_model.evaluate(
                FloodRiskInput(
                    rainfall_mm=snap.rainfall_mm,
                    rainfall_intensity=rain.intensity_mm_h,
                    river_level_m=snap.river_level_m,
                    historical_flood_frequency=0.62,
                    terrain_elevation_m=2.5,
                    soil_saturation=0.78,
                )
            )
            return overlay_demo_flood(result)
        if snap is None and rain is None:
            raise ProviderUnavailableError(
                "risk",
                "Flood score unavailable: OpenWeather and NASA POWER both failed. No fabricated rainfall or river level.",
            )
        result = self.flood_model.evaluate(
            FloodRiskInput(
                rainfall_mm=snap.rainfall_mm if snap is not None else None,
                rainfall_intensity=rain.intensity_mm_h if rain is not None else None,
                river_level_m=None,
                historical_flood_frequency=None,
                terrain_elevation_m=None,
                soil_saturation=None,
            )
        )
        return result.__class__(
            flood_probability=result.flood_probability,
            risk_score=result.risk_score,
            risk_level=result.risk_level,
            factors=result.factors,
            recommended_action=result.recommended_action,
            estimate_label=result.estimate_label,
        )

    def cyclone(self, location_id: str | None):
        snap = self.current(location_id)
        trend = None
        try:
            fc = self.forecast(location_id)
            trend = _wind_trend(fc)
        except ProviderUnavailableError:
            trend = None
        from app.services.geo.aoi import get_aoi

        region = str(get_aoi().get("aoi_name") or settings.aoi_name)
        result = evaluate_cyclone(
            snap.wind_speed_ms,
            snap.pressure_hpa,
            None if not settings.use_mock_providers else snap.storm_probability,
            trend,
            region=region,
        )
        if not settings.use_mock_providers:
            return result.__class__(
                cyclone_risk=result.cyclone_risk,
                severity=result.severity,
                affected_region=result.affected_region,
                recommended_action=result.recommended_action,
                storm_probability=result.storm_probability,
                estimate_label=(
                    "RULE-BASED cyclone index from OpenWeather wind/pressure — not an official IMD cyclone warning."
                ),
            )
        return result

    def weather_alerts(self, location_id: str | None):
        imd_note = "IMD not queried."
        imd_source_status = "UNAVAILABLE"
        provider_alerts = []
        try:
            provider_alerts = self.provider.alerts(location_id)
            if settings.use_mock_providers:
                imd_source_status = "MOCK"
                imd_note = "Demo Mode mock provider alerts — not official IMD warnings."
            elif not provider_alerts:
                imd_source_status = "LIVE_EMPTY"
                imd_note = (
                    "IMD API returned no district warnings in this payload. "
                    "That is not confirmation that no warnings exist elsewhere."
                )
            else:
                imd_source_status = "LIVE"
                imd_note = "IMD district warnings from configured API."
        except ProviderUnavailableError as exc:
            provider_alerts = []
            msg = exc.message or ""
            if "NOT_CONFIGURED" in msg or "not configured" in msg.lower() or "IMD_API_KEY" in msg:
                imd_source_status = "NOT_CONFIGURED"
            else:
                imd_source_status = "UNAVAILABLE"
            imd_note = msg or "IMD warning source unavailable."
        flood = None
        cyclone = None
        try:
            flood = self.flood(location_id)
        except ProviderUnavailableError:
            flood = None
        try:
            cyclone = self.cyclone(location_id)
        except ProviderUnavailableError:
            cyclone = None
        generated = []
        if self.db is not None:
            if flood is not None and should_raise_flood_alert(flood.flood_probability):
                alert = persist_alert_candidate(
                    self.db,
                    title="Prototype flood risk threshold exceeded",
                    severity="critical",
                    message=(
                        "Derived risk estimate (not an official government warning). "
                        f"{flood.estimate_label}: index "
                        f"{flood.flood_probability:.0f}. {flood.recommended_action} "
                        "No SMS/email dispatched. Not an IMD warning."
                    ),
                    location_id=location_id,
                )
                generated.append(alert)
            if cyclone is not None and should_raise_cyclone_alert(cyclone.cyclone_risk):
                alert = persist_alert_candidate(
                    self.db,
                    title="Prototype cyclone risk threshold exceeded",
                    severity="warning",
                    message=(
                        "Derived risk estimate (not an official government warning). "
                        f"{cyclone.estimate_label}: index {cyclone.cyclone_risk:.0f}. "
                        f"{cyclone.recommended_action} No SMS/email dispatched. Not an IMD warning."
                    ),
                    location_id=location_id,
                )
                generated.append(alert)
        return {
            "provider_alerts": provider_alerts,
            "generated_candidates": generated,
            "flood_probability": flood.flood_probability if flood else 0.0,
            "cyclone_risk": cyclone.cyclone_risk if cyclone else 0.0,
            "imd_status": imd_note,
            "imd_source_status": imd_source_status,
        }


ZONE_PROFILES = {
    "Polder A floodplain": {
        "population": 42000,
        "historical": 0.74,
        "elevation": 1.8,
        "soil": 0.88,
    },
    "Hill ward 12": {
        "population": 8500,
        "historical": 0.41,
        "elevation": 48.0,
        "soil": 0.35,
    },
    "Coastal surge belt": {
        "population": 19000,
        "historical": 0.55,
        "elevation": 4.0,
        "soil": 0.5,
    },
}
