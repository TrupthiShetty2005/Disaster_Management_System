import numpy as np
import pytest

from app.services import fire, rainfall, satellite, water


def test_gumbel_levels_increase_with_return_period():
    maxima = [3200, 4100, 5200, 2800, 6100, 4700, 3900, 7300, 4400, 5100, 3600, 13300]
    q = water.gumbel_return_levels(maxima)
    assert q["q2"] < q["q5"] < q["q20"]
    # 2-year level sits just below the mean of the annual maxima for a Gumbel fit
    assert q["q2"] < np.mean(maxima)


@pytest.mark.parametrize(
    ("flow", "expected"),
    [(None, "NORMAL"), (500, "NORMAL"), (1000, "WATCH"), (1600, "WARNING"), (2500, "SEVERE")],
)
def test_station_level_against_return_levels(flow, expected):
    th = {"q2": 1000, "q5": 1500, "q20": 2400}
    assert water._level(flow, th) == expected


def test_level_is_unknown_without_thresholds():
    assert water._level(900, None) is None


@pytest.mark.parametrize(
    ("mm", "category"),
    [(None, "NO_DATA"), (0, "NO_RAIN"), (2.4, "VERY_LIGHT"), (15.5, "LIGHT"), (15.6, "MODERATE"), (64.5, "HEAVY"), (115.6, "VERY_HEAVY"), (204.5, "EXTREMELY_HEAVY")],
)
def test_imd_rainfall_categories(mm, category):
    assert rainfall.imd_category(mm) == category


def test_fosberg_index_rises_with_heat_dryness_and_wind():
    calm_humid = fire.fosberg_ffwi(24, 85, 5)
    hot_dry = fire.fosberg_ffwi(38, 15, 5)
    hot_dry_windy = fire.fosberg_ffwi(38, 15, 40)
    assert calm_humid < hot_dry < hot_dry_windy
    assert fire.ffwi_class(calm_humid) == "LOW"
    assert fire.ffwi_class(hot_dry_windy) in {"HIGH", "VERY_HIGH", "EXTREME"}


def test_otsu_threshold_finds_valley_between_water_and_land():
    rng = np.random.default_rng(0)
    water_db = rng.normal(-21, 1.0, 4000)
    land_db = rng.normal(-9, 1.5, 12000)
    t = satellite.otsu_threshold(np.concatenate([water_db, land_db]))
    assert -18 < t < -12


def test_otsu_threshold_is_clamped():
    assert satellite.otsu_threshold(np.full(1000, -5.0)) >= -24
    assert satellite.otsu_threshold(np.array([])) == -18.0


def test_resolve_area_rejects_oversized_boxes():
    with pytest.raises(ValueError):
        satellite.resolve_area({"bbox": [75.0, 14.0, 76.5, 15.5]})
    name, bbox = satellite.resolve_area({"station": "almatti"})
    assert "Almatti" in name and bbox[0] < 75.8875 < bbox[2]
