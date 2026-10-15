from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base, new_uuid


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Location(Base):
    __tablename__ = "locations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(255))
    district: Mapped[str] = mapped_column(String(255))
    state: Mapped[str] = mapped_column(String(255))
    country: Mapped[str] = mapped_column(String(64), default="India")
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    geojson = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)


class Disaster(Base):
    __tablename__ = "disasters"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    title: Mapped[str] = mapped_column(String(255))
    disaster_type: Mapped[str] = mapped_column(String(64))
    phase: Mapped[str] = mapped_column(String(32))  # precaution | response | recovery
    severity: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32), default="active")
    people_at_risk: Mapped[int] = mapped_column(Integer, default=0)
    location_id: Mapped[str] = mapped_column(ForeignKey("locations.id"))
    geojson = mapped_column(JSON, nullable=True)
    summary: Mapped[str] = mapped_column(Text, default="")
    started_at: Mapped[datetime] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

    location: Mapped[Location] = relationship()


class RiskZone(Base):
    __tablename__ = "risk_zones"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(255))
    hazard_type: Mapped[str] = mapped_column(String(64))
    risk_score: Mapped[float] = mapped_column(Float)
    risk_level: Mapped[str] = mapped_column(String(32))
    location_id: Mapped[str] = mapped_column(ForeignKey("locations.id"))
    geojson = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)


class WeatherObservation(Base):
    __tablename__ = "weather_observations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    location_id: Mapped[str] = mapped_column(ForeignKey("locations.id"))
    source: Mapped[str] = mapped_column(String(64), default="mock")
    temperature_c: Mapped[float] = mapped_column(Float)
    humidity: Mapped[float] = mapped_column(Float)
    rainfall_mm: Mapped[float] = mapped_column(Float)
    wind_speed_ms: Mapped[float] = mapped_column(Float)
    pressure_hpa: Mapped[float] = mapped_column(Float)
    conditions: Mapped[str] = mapped_column(String(128))
    observed_at: Mapped[datetime] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class WeatherForecast(Base):
    __tablename__ = "weather_forecasts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    location_id: Mapped[str] = mapped_column(ForeignKey("locations.id"))
    source: Mapped[str] = mapped_column(String(64), default="mock")
    period_start: Mapped[datetime] = mapped_column(DateTime)
    period_end: Mapped[datetime] = mapped_column(DateTime)
    temperature_c: Mapped[float] = mapped_column(Float)
    rainfall_mm: Mapped[float] = mapped_column(Float)
    wind_speed_ms: Mapped[float] = mapped_column(Float)
    conditions: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class SatelliteImage(Base):
    __tablename__ = "satellite_images"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    location_id: Mapped[str] = mapped_column(ForeignKey("locations.id"))
    captured_at: Mapped[datetime] = mapped_column(DateTime)
    provider: Mapped[str] = mapped_column(String(64), default="demo")
    source: Mapped[str] = mapped_column(String(64), default="mock-sentinel2")
    storage_path: Mapped[str] = mapped_column(String(512))
    bbox_geojson = mapped_column(JSON, nullable=True)
    latitude: Mapped[float] = mapped_column(Float, default=9.517)
    longitude: Mapped[float] = mapped_column(Float, default=76.522)
    resolution: Mapped[str] = mapped_column(String(32), default="10m")
    cloud_cover: Mapped[float] = mapped_column(Float, default=8.0)
    image_url: Mapped[str] = mapped_column(String(512), default="")
    thumbnail_url: Mapped[str] = mapped_column(String(512), default="")
    status: Mapped[str] = mapped_column(String(32), default="ready")
    extra_metadata = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class ImageAnalysisResult(Base):
    __tablename__ = "image_analysis_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    satellite_image_id: Mapped[str] = mapped_column(ForeignKey("satellite_images.id"))
    model_name: Mapped[str] = mapped_column(String(128))
    analysis_type: Mapped[str] = mapped_column(String(64))
    summary: Mapped[str] = mapped_column(Text, default="")
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    result_geojson = mapped_column(JSON, nullable=True)
    metrics = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class DetectedObject(Base):
    __tablename__ = "detected_objects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    analysis_id: Mapped[str] = mapped_column(ForeignKey("image_analysis_results.id"))
    label: Mapped[str] = mapped_column(String(64))
    confidence: Mapped[float] = mapped_column(Float)
    bbox_geojson = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class FloodEvent(Base):
    __tablename__ = "flood_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    disaster_id: Mapped[str] = mapped_column(ForeignKey("disasters.id"))
    water_depth_m: Mapped[float] = mapped_column(Float)
    extent_km2: Mapped[float] = mapped_column(Float)
    geojson = mapped_column(JSON, nullable=True)
    detected_at: Mapped[datetime] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class DamageAssessment(Base):
    __tablename__ = "damage_assessments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    disaster_id: Mapped[str] = mapped_column(ForeignKey("disasters.id"))
    target_type: Mapped[str] = mapped_column(String(64))
    damage_class: Mapped[str] = mapped_column(String(64))
    confidence: Mapped[float] = mapped_column(Float)
    notes: Mapped[str] = mapped_column(Text, default="")
    geojson = mapped_column(JSON, nullable=True)
    assessed_at: Mapped[datetime] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class Infrastructure(Base):
    __tablename__ = "infrastructure"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(255))
    category: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32))
    location_id: Mapped[str] = mapped_column(ForeignKey("locations.id"))
    geojson = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)


class Road(Base):
    __tablename__ = "roads"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(255))
    accessibility: Mapped[str] = mapped_column(String(32))
    location_id: Mapped[str] = mapped_column(ForeignKey("locations.id"))
    geojson = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)


class Building(Base):
    __tablename__ = "buildings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(255))
    occupancy: Mapped[str] = mapped_column(String(64))
    damage_class: Mapped[str] = mapped_column(String(64), default="unknown")
    location_id: Mapped[str] = mapped_column(ForeignKey("locations.id"))
    geojson = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)


class RescueResource(Base):
    __tablename__ = "rescue_resources"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(255))
    resource_type: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32))
    personnel: Mapped[int] = mapped_column(Integer, default=0)
    capacity: Mapped[int] = mapped_column(Integer, default=0)
    latitude: Mapped[float] = mapped_column(Float, default=9.517)
    longitude: Mapped[float] = mapped_column(Float, default=76.522)
    available_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    assigned_incident: Mapped[str | None] = mapped_column(String(36), nullable=True)
    location_id: Mapped[str] = mapped_column(ForeignKey("locations.id"))
    geojson = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)


class EvacuationCenter(Base):
    __tablename__ = "evacuation_centers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(255))
    capacity: Mapped[int] = mapped_column(Integer)
    occupied: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(32), default="open")
    location_id: Mapped[str] = mapped_column(ForeignKey("locations.id"))
    geojson = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)


class RescuePriority(Base):
    __tablename__ = "rescue_priorities"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    disaster_id: Mapped[str] = mapped_column(ForeignKey("disasters.id"))
    title: Mapped[str] = mapped_column(String(255))
    priority: Mapped[int] = mapped_column(Integer)
    people_affected: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32))
    score: Mapped[float] = mapped_column(Float, default=0)
    level: Mapped[str] = mapped_column(String(32), default="MEDIUM")
    factors = mapped_column(JSON, nullable=True)
    geojson = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)


class RescuePlan(Base):
    __tablename__ = "rescue_plans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    disaster_id: Mapped[str] = mapped_column(ForeignKey("disasters.id"))
    priority_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    decision: Mapped[str] = mapped_column(String(32), default="PENDING")
    override_notes: Mapped[str] = mapped_column(Text, default="")
    payload = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    title: Mapped[str] = mapped_column(String(255))
    severity: Mapped[str] = mapped_column(String(32))
    category: Mapped[str] = mapped_column(String(64))
    alert_type: Mapped[str] = mapped_column(String(64), default="weather")
    message: Mapped[str] = mapped_column(Text)
    location_id: Mapped[str | None] = mapped_column(ForeignKey("locations.id"), nullable=True)
    location_name: Mapped[str] = mapped_column(String(255), default="")
    latitude: Mapped[float] = mapped_column(Float, default=9.517)
    longitude: Mapped[float] = mapped_column(Float, default=76.522)
    risk_score: Mapped[float] = mapped_column(Float, default=0)
    issued_at: Mapped[datetime] = mapped_column(DateTime)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE")
    recommended_action: Mapped[str] = mapped_column(Text, default="")
    source: Mapped[str] = mapped_column(String(64), default="engine")
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    acknowledged_by: Mapped[str] = mapped_column(String(255), default="")
    reason: Mapped[str] = mapped_column(Text, default="")
    signals = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255), unique=True)
    role: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    actor_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(128))
    entity_type: Mapped[str] = mapped_column(String(64))
    entity_id: Mapped[str] = mapped_column(String(36))
    details: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class VisionJob(Base):
    __tablename__ = "vision_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    original_filename: Mapped[str] = mapped_column(String(255))
    upload_path: Mapped[str] = mapped_column(String(512))
    annotated_path: Mapped[str] = mapped_column(String(512), default="")
    model_name: Mapped[str] = mapped_column(String(128))
    backend: Mapped[str] = mapped_column(String(32), default="demo")
    overall_severity: Mapped[str] = mapped_column(String(32), default="low")
    processing_ms: Mapped[float] = mapped_column(Float, default=0)
    detections = mapped_column(JSON, nullable=True)
    incident = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class FloodAnalysis(Base):
    __tablename__ = "flood_analyses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    model_name: Mapped[str] = mapped_column(String(128))
    scene_kind: Mapped[str] = mapped_column(String(64), default="flood")
    flooded_area: Mapped[float] = mapped_column(Float, default=0)
    flood_percentage: Mapped[float] = mapped_column(Float, default=0)
    severity: Mapped[str] = mapped_column(String(32), default="low")
    confidence: Mapped[float] = mapped_column(Float, default=0.55)
    affected_population: Mapped[int] = mapped_column(Integer, default=0)
    affected_roads: Mapped[int] = mapped_column(Integer, default=0)
    affected_buildings: Mapped[int] = mapped_column(Integer, default=0)
    boundary_geojson = mapped_column(JSON, nullable=True)
    heatmap_geojson = mapped_column(JSON, nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class DamageReport(Base):
    __tablename__ = "damage_reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    model_name: Mapped[str] = mapped_column(String(128), default="demo-change-v0")
    before_kind: Mapped[str] = mapped_column(String(64), default="flood_before")
    after_kind: Mapped[str] = mapped_column(String(64), default="flood")
    report = mapped_column(JSON, nullable=True)
    overlay_geojson = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
