from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models import (
    Alert,
    AuditLog,
    Building,
    DamageAssessment,
    DetectedObject,
    Disaster,
    EvacuationCenter,
    FloodEvent,
    ImageAnalysisResult,
    Infrastructure,
    Location,
    RescuePriority,
    RescueResource,
    RiskZone,
    Road,
    SatelliteImage,
    User,
    WeatherForecast,
    WeatherObservation,
)

# Demo IDs — deterministic for tests and frontend mock alignment
LOC_KUTTANAD = "11111111-1111-4111-8111-111111111111"
LOC_GUWAHATI = "22222222-2222-4222-8222-222222222222"
LOC_PURI = "33333333-3333-4333-8333-333333333333"
DIS_FLOOD = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
DIS_LANDSLIDE = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
DIS_CYCLONE = "cccccccc-cccc-4ccc-8ccc-cccccccccccc"

NOW = datetime(2026, 7, 14, 6, 0, 0)


def _point(lon: float, lat: float) -> dict:
    return {"type": "Point", "coordinates": [lon, lat]}


def _poly(coords: list[list[float]]) -> dict:
    ring = coords + [coords[0]]
    return {"type": "Polygon", "coordinates": [ring]}


def seed_if_empty() -> None:
    db = SessionLocal()
    try:
        if db.query(Disaster).count() > 0:
            return
        seed(db)
    finally:
        db.close()


def seed(db: Session) -> None:
    kuttanad = Location(
        id=LOC_KUTTANAD,
        name="Kuttanad Wetlands (demo)",
        district="Alappuzha",
        state="Kerala",
        latitude=9.517,
        longitude=76.522,
        geojson=_point(76.522, 9.517),
    )
    guwahati = Location(
        id=LOC_GUWAHATI,
        name="Brahmaputra Belt (demo)",
        district="Kamrup Metro",
        state="Assam",
        latitude=26.185,
        longitude=91.752,
        geojson=_point(91.752, 26.185),
    )
    puri = Location(
        id=LOC_PURI,
        name="Puri Coastal Belt (demo)",
        district="Puri",
        state="Odisha",
        latitude=19.813,
        longitude=85.831,
        geojson=_point(85.831, 19.813),
    )
    db.add_all([kuttanad, guwahati, puri])

    flood = Disaster(
        id=DIS_FLOOD,
        title="Kuttanad monsoon inundation (demo)",
        disaster_type="flood",
        phase="response",
        severity="high",
        status="active",
        people_at_risk=42000,
        location_id=LOC_KUTTANAD,
        geojson=_point(76.522, 9.517),
        summary="Fictional demo of prolonged rainfall and embankment stress in Kuttanad polders.",
        started_at=NOW - timedelta(days=2),
    )
    slide = Disaster(
        id=DIS_LANDSLIDE,
        title="Guwahati hillslope displacement (demo)",
        disaster_type="landslide",
        phase="precaution",
        severity="medium",
        status="monitoring",
        people_at_risk=8500,
        location_id=LOC_GUWAHATI,
        geojson=_point(91.752, 26.185),
        summary="Demo slope-risk watch after concentrated rainfall. Not an official bulletin.",
        started_at=NOW - timedelta(hours=18),
    )
    cyclone = Disaster(
        id=DIS_CYCLONE,
        title="Bay of Bengal cyclone track (demo)",
        disaster_type="cyclone",
        phase="recovery",
        severity="severe",
        status="recovering",
        people_at_risk=110000,
        location_id=LOC_PURI,
        geojson=_point(85.831, 19.813),
        summary="Post-landfall recovery demo: debris, blocked roads, shelter occupancy.",
        started_at=NOW - timedelta(days=6),
    )
    db.add_all([flood, slide, cyclone])

    db.add_all(
        [
            RiskZone(
                name="Polder A floodplain",
                hazard_type="flood",
                risk_score=0.86,
                risk_level="high",
                location_id=LOC_KUTTANAD,
                geojson=_poly([[76.50, 9.50], [76.55, 9.50], [76.55, 9.54], [76.50, 9.54]]),
            ),
            RiskZone(
                name="Hill ward 12",
                hazard_type="landslide",
                risk_score=0.71,
                risk_level="high",
                location_id=LOC_GUWAHATI,
                geojson=_poly([[91.73, 26.17], [91.77, 26.17], [91.77, 26.20], [91.73, 26.20]]),
            ),
            RiskZone(
                name="Coastal surge belt",
                hazard_type="cyclone",
                risk_score=0.64,
                risk_level="medium",
                location_id=LOC_PURI,
                geojson=_poly([[85.80, 19.79], [85.86, 19.79], [85.86, 19.83], [85.80, 19.83]]),
            ),
        ]
    )

    db.add(
        WeatherObservation(
            location_id=LOC_KUTTANAD,
            source="mock",
            temperature_c=27.4,
            humidity=94.0,
            rainfall_mm=48.2,
            wind_speed_ms=6.1,
            pressure_hpa=1004.0,
            conditions="Heavy rain",
            observed_at=NOW,
        )
    )
    for i in range(5):
        db.add(
            WeatherForecast(
                location_id=LOC_KUTTANAD,
                source="mock",
                period_start=NOW + timedelta(hours=i * 6),
                period_end=NOW + timedelta(hours=(i + 1) * 6),
                temperature_c=26.0 + i * 0.3,
                rainfall_mm=12.0 - i,
                wind_speed_ms=5.0 + i * 0.4,
                conditions="Rain" if i < 3 else "Showers",
            )
        )

    sat = SatelliteImage(
        location_id=LOC_KUTTANAD,
        captured_at=NOW - timedelta(hours=4),
        provider="demo-stub",
        storage_path="data/mock/satellite/kuttanad_demo.txt",
        bbox_geojson=_poly([[76.49, 9.49], [76.56, 9.49], [76.56, 9.55], [76.49, 9.55]]),
    )
    db.add(sat)
    db.flush()
    analysis = ImageAnalysisResult(
        satellite_image_id=sat.id,
        model_name="stub-flood-seg-v0",
        analysis_type="flood",
        summary="Stub detector: water extent over demo polders. Not a live model.",
        confidence=0.81,
        result_geojson=_poly([[76.51, 9.51], [76.54, 9.51], [76.54, 9.53], [76.51, 9.53]]),
    )
    db.add(analysis)
    db.flush()
    db.add(
        DetectedObject(
            analysis_id=analysis.id,
            label="rescue_boat",
            confidence=0.76,
            bbox_geojson=_poly([[76.521, 9.518], [76.523, 9.518], [76.523, 9.520], [76.521, 9.520]]),
        )
    )

    db.add(
        FloodEvent(
            disaster_id=DIS_FLOOD,
            water_depth_m=1.8,
            extent_km2=34.5,
            geojson=_poly([[76.51, 9.51], [76.54, 9.51], [76.54, 9.53], [76.51, 9.53]]),
            detected_at=NOW - timedelta(hours=3),
        )
    )
    db.add(
        DamageAssessment(
            disaster_id=DIS_FLOOD,
            target_type="building",
            damage_class="moderate",
            confidence=0.72,
            notes="Stub classification of a demo dwelling cluster.",
            geojson=_point(76.528, 9.521),
            assessed_at=NOW - timedelta(hours=2),
        )
    )
    db.add_all(
        [
            Infrastructure(
                name="Kuttanad pump house (demo)",
                category="waterworks",
                status="degraded",
                location_id=LOC_KUTTANAD,
                geojson=_point(76.530, 9.515),
            ),
            Road(
                name="Alappuzha–Changanassery stretch (demo)",
                accessibility="blocked",
                location_id=LOC_KUTTANAD,
                geojson={
                    "type": "LineString",
                    "coordinates": [[76.51, 9.52], [76.54, 9.525]],
                },
            ),
            Road(
                name="Polder feeder road east (demo)",
                accessibility="blocked",
                location_id=LOC_KUTTANAD,
                geojson={"type": "LineString", "coordinates": [[76.52, 9.51], [76.53, 9.515]]},
            ),
            Road(
                name="Bund service track (demo)",
                accessibility="blocked",
                location_id=LOC_KUTTANAD,
                geojson={"type": "LineString", "coordinates": [[76.515, 9.518], [76.528, 9.52]]},
            ),
            Building(
                name="Panchayat hall (demo)",
                occupancy="public",
                damage_class="minor",
                location_id=LOC_KUTTANAD,
                geojson=_point(76.519, 9.516),
            ),
            RescueResource(
                name="Boat unit Delta (demo)",
                resource_type="rescue_boat",
                status="deployed",
                personnel=8,
                location_id=LOC_KUTTANAD,
                geojson=_point(76.525, 9.519),
            ),
            RescueResource(
                name="Ambulance 12 (demo)",
                resource_type="ambulance",
                status="staging",
                personnel=3,
                location_id=LOC_KUTTANAD,
                geojson=_point(76.535, 9.510),
            ),
            RescueResource(
                name="Medical team C (demo)",
                resource_type="medical_team",
                status="deployed",
                personnel=6,
                location_id=LOC_PURI,
                geojson=_point(85.835, 19.815),
            ),
            EvacuationCenter(
                name="Community school shelter (demo)",
                capacity=800,
                occupied=540,
                status="open",
                location_id=LOC_KUTTANAD,
                geojson=_point(76.540, 9.508),
            ),
            EvacuationCenter(
                name="Cyclone shelter block B (demo)",
                capacity=1200,
                occupied=310,
                status="open",
                location_id=LOC_PURI,
                geojson=_point(85.840, 19.820),
            ),
            RescuePriority(
                disaster_id=DIS_FLOOD,
                title="Isolate polder hamlet cluster",
                priority=1,
                people_affected=1200,
                status="in_progress",
                geojson=_point(76.527, 9.522),
            ),
            Alert(
                title="Heavy rainfall watch (demo)",
                severity="warning",
                category="weather",
                message="Demo alert: 40–60 mm/6h possible over Kuttanad wetlands. Not an IMD product.",
                location_id=LOC_KUTTANAD,
                issued_at=NOW - timedelta(hours=1),
            ),
            Alert(
                title="Road closure — NH demo segment",
                severity="critical",
                category="accessibility",
                message="Demo: inundated carriageway; boats preferred for last-mile access.",
                location_id=LOC_KUTTANAD,
                issued_at=NOW - timedelta(minutes=40),
            ),
            User(
                name="Ops Coordinator",
                email="ops.demo@visionguard.local",
                role="coordinator",
            ),
        ]
    )
    db.flush()
    db.add(
        AuditLog(
            action="seed",
            entity_type="database",
            entity_id="bootstrap",
            details="Deterministic demo seed loaded.",
        )
    )
    db.commit()


if __name__ == "__main__":
    from app.db.init_db import init_db

    init_db()
    seed_if_empty()
    print("Database seeded.")
