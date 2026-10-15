from app.services.risk.cyclone import evaluate_cyclone
from app.services.risk.flood import BaselineFloodRiskModel, FloodRiskInput
from app.services.risk.pipeline import should_raise_cyclone_alert, should_raise_flood_alert
from app.services.risk.rainfall import analyze_rainfall
from app.services.weather.mock_provider import MockWeatherProvider


def test_mock_weather_current_shape():
    snap = MockWeatherProvider().current(None)
    assert snap.temperature_c > 0
    assert snap.humidity > 0
    assert snap.rainfall_mm >= 0
    assert snap.visibility_km > 0
    assert snap.provider_live is False


def test_rainfall_calculation():
    result = analyze_rainfall([10, 12, 40])
    assert result.cumulative_mm == 62
    assert result.intensity_mm_h > 0
    assert 0 <= result.short_term_risk <= 100
    assert result.anomaly > 0


def test_flood_probability_and_score():
    result = BaselineFloodRiskModel().evaluate(
        FloodRiskInput(
            rainfall_mm=48.2,
            rainfall_intensity=2.0,
            river_level_m=3.1,
            historical_flood_frequency=0.62,
            terrain_elevation_m=2.5,
            soil_saturation=0.78,
        )
    )
    assert 0 <= result.flood_probability <= 100
    assert "RULE-BASED" in result.estimate_label or "Prototype" in result.estimate_label
    assert result.risk_level in {"low", "moderate", "high", "critical"}
    assert result.factors


def test_alert_thresholds():
    assert should_raise_flood_alert(82) is True
    assert should_raise_flood_alert(10) is False
    assert should_raise_cyclone_alert(61) is True
    assert should_raise_cyclone_alert(10) is False


def test_cyclone_output():
    result = evaluate_cyclone(18, 990, 0.7, 4.0)
    assert result.affected_region
    assert result.recommended_action
    assert 0 <= result.cyclone_risk <= 100
