"""Major Karnataka industrial hazard sites watched for satellite thermal anomalies.

Coordinates are the OpenStreetMap feature centroids (landuse=industrial / power=plant), looked up via
Nominatim and Overpass. `radius_km` is the search radius for FIRMS detections around the site centre.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class Facility:
    name: str
    latitude: float
    longitude: float


@dataclass(frozen=True)
class IndustrialSite:
    id: str
    name: str
    kind: str
    district_id: str
    latitude: float
    longitude: float
    radius_km: float
    facilities: tuple[Facility, ...] = field(default_factory=tuple)


SITES: tuple[IndustrialSite, ...] = (
    IndustrialSite(
        "mrpl", "MRPL refinery (Kuthethoor–Bajpe, Mangaluru)", "Oil refinery & petrochemicals (flare stacks)", "dakshina-kannada", 12.9856, 74.8429, 4.0,
        (Facility("Mangalore Refinery & Petrochemicals Ltd", 12.9856, 74.8429), Facility("ONGC Mangalore Petrochemicals (OMPL)", 12.9962, 74.8662)),
    ),
    IndustrialSite(
        "panambur-baikampady", "Panambur–Baikampady industrial belt (Mangaluru)", "Port, fertiliser, chemicals, iron-ore pellets, fuel depots", "dakshina-kannada", 12.9450, 74.8200, 4.0,
        (
            Facility("Baikampady Industrial Area (KIADB)", 12.9492, 74.8201),
            Facility("New Mangalore Port (NMPT)", 12.9298, 74.8225),
            Facility("KIOCL iron-ore pellet plant", 12.9251, 74.8219),
            Facility("Mangalore Chemicals & Fertilizers", 12.9341, 74.8241),
            Facility("BASF India", 12.9793, 74.8245),
            Facility("BPCL Mangalore coastal installation", 12.9602, 74.8123),
            Facility("Total Oil India LPG", 12.9485, 74.8357),
        ),
    ),
    IndustrialSite(
        "upcl", "Udupi Power Corporation (Yellur–Padubidri)", "Coal-fired power plant", "udupi", 13.1600, 74.8030, 3.0,
        (Facility("Udupi Power Corporation Ltd (Adani Power)", 13.1600, 74.8030), Facility("Nandikur Industrial Area", 13.1499, 74.8072)),
    ),
    IndustrialSite("kaiga", "Kaiga Atomic Power Station", "Nuclear power plant", "uttara-kannada", 14.8661, 74.4384, 3.0),
    IndustrialSite(
        "jsw-toranagallu", "JSW Steel Vijayanagar Works (Toranagallu)", "Integrated steel plant & captive power", "ballari", 15.1818, 76.6694, 5.0,
        (Facility("JSW Steel (Jindal Steel Works)", 15.1818, 76.6694), Facility("JSW Energy Toranagallu power station", 15.1851, 76.6647)),
    ),
    IndustrialSite(
        "kudathini", "Kudathini steel & sponge-iron cluster (Ballari)", "Sponge iron, steel, cement", "ballari", 15.1750, 76.7900, 5.0,
        (Facility("Shatavahana Kudatini Steels", 15.2251, 76.7649), Facility("Agarwal Sponge Iron", 15.1698, 76.7844), Facility("ACC cement", 15.2168, 76.7804)),
    ),
    IndustrialSite("rtps", "Raichur Thermal Power Station (Shaktinagar)", "Coal-fired power plant", "raichur", 16.3606, 77.3367, 3.0),
    IndustrialSite("yermarus", "Yermarus Thermal Power Station", "Coal-fired power plant", "raichur", 16.2963, 77.3569, 3.0),
    IndustrialSite("kudgi", "NTPC Kudgi Super Thermal Power Project", "Coal-fired power plant", "vijayapura", 16.5044, 75.8381, 3.0),
    IndustrialSite("visl", "Visvesvaraya Iron & Steel Plant (Bhadravati)", "Steel plant", "shivamogga", 13.8314, 75.7045, 3.0),
    IndustrialSite("bidadi", "Bidadi Industrial Area", "Automobile & manufacturing (KIADB)", "ramanagara", 12.7806, 77.4163, 3.0),
)

SITES_BY_ID = {s.id: s for s in SITES}


def site_dicts() -> list[dict[str, Any]]:
    return [asdict(s) for s in SITES]
