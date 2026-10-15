from sqlalchemy import text

from app.db.session import Base, engine
from app.models import (  # noqa: F401
    Alert,
    AuditLog,
    Building,
    DamageAssessment,
    DamageReport,
    DetectedObject,
    Disaster,
    EvacuationCenter,
    FloodAnalysis,
    FloodEvent,
    ImageAnalysisResult,
    Infrastructure,
    Location,
    RescuePlan,
    RescuePriority,
    RescueResource,
    RiskZone,
    Road,
    SatelliteImage,
    User,
    VisionJob,
    WeatherForecast,
    WeatherObservation,
)


def _sqlite_add_column(table: str, column: str, ddl: str) -> None:
    if not str(engine.url).startswith("sqlite"):
        return
    with engine.connect() as conn:
        rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
        existing = {row[1] for row in rows}
        if column not in existing and rows:
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {ddl}"))
            conn.commit()


def migrate_satellite_schema() -> None:
    for col, ddl in [
        ("source", "source VARCHAR(64) DEFAULT 'mock-sentinel2'"),
        ("latitude", "latitude FLOAT DEFAULT 9.517"),
        ("longitude", "longitude FLOAT DEFAULT 76.522"),
        ("resolution", "resolution VARCHAR(32) DEFAULT '10m'"),
        ("cloud_cover", "cloud_cover FLOAT DEFAULT 8.0"),
        ("image_url", "image_url VARCHAR(512) DEFAULT ''"),
        ("thumbnail_url", "thumbnail_url VARCHAR(512) DEFAULT ''"),
        ("status", "status VARCHAR(32) DEFAULT 'ready'"),
        ("extra_metadata", "extra_metadata JSON"),
    ]:
        _sqlite_add_column("satellite_images", col, ddl)
    _sqlite_add_column("image_analysis_results", "metrics", "metrics JSON")


def migrate_rescue_schema() -> None:
    for col, ddl in [
        ("capacity", "capacity INTEGER DEFAULT 0"),
        ("latitude", "latitude FLOAT DEFAULT 9.517"),
        ("longitude", "longitude FLOAT DEFAULT 76.522"),
        ("available_at", "available_at DATETIME"),
        ("assigned_incident", "assigned_incident VARCHAR(36)"),
    ]:
        _sqlite_add_column("rescue_resources", col, ddl)
    for col, ddl in [
        ("score", "score FLOAT DEFAULT 0"),
        ("level", "level VARCHAR(32) DEFAULT 'MEDIUM'"),
        ("factors", "factors JSON"),
    ]:
        _sqlite_add_column("rescue_priorities", col, ddl)


def migrate_alert_schema() -> None:
    for col, ddl in [
        ("alert_type", "alert_type VARCHAR(64) DEFAULT 'weather'"),
        ("location_name", "location_name VARCHAR(255) DEFAULT ''"),
        ("latitude", "latitude FLOAT DEFAULT 9.517"),
        ("longitude", "longitude FLOAT DEFAULT 76.522"),
        ("risk_score", "risk_score FLOAT DEFAULT 0"),
        ("expires_at", "expires_at DATETIME"),
        ("status", "status VARCHAR(32) DEFAULT 'ACTIVE'"),
        ("recommended_action", "recommended_action TEXT DEFAULT ''"),
        ("source", "source VARCHAR(64) DEFAULT 'engine'"),
        ("acknowledged_at", "acknowledged_at DATETIME"),
        ("acknowledged_by", "acknowledged_by VARCHAR(255) DEFAULT ''"),
        ("reason", "reason TEXT DEFAULT ''"),
        ("signals", "signals JSON"),
    ]:
        _sqlite_add_column("alerts", col, ddl)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    migrate_satellite_schema()
    migrate_rescue_schema()
    migrate_alert_schema()
