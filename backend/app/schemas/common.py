from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class LocationOut(ORMModel):
    id: str
    name: str
    district: str
    state: str
    country: str
    latitude: float
    longitude: float
    geojson: Any | None = None


class DisasterOut(ORMModel):
    id: str
    title: str
    disaster_type: str
    phase: str
    severity: str
    status: str
    people_at_risk: int
    location_id: str
    geojson: Any | None = None
    summary: str
    started_at: datetime
    location: LocationOut | None = None


class DisasterList(BaseModel):
    items: list[DisasterOut]
    total: int


class FactorOut(BaseModel):
    name: str
    level: str
    value: float


class RiskZoneOut(ORMModel):
    id: str
    name: str
    hazard_type: str
    risk_score: float
    risk_level: str
    location_id: str
    geojson: Any | None = None
    flood_probability: float | None = None
    affected_population: int | None = None
    contributing_factors: list[FactorOut] | None = None
    recommended_action: str | None = None
    estimate_label: str | None = None


class RiskZoneDetailOut(RiskZoneOut):
    pass


class RiskZoneList(BaseModel):
    items: list[RiskZoneOut]
    total: int


class WeatherCurrentOut(BaseModel):
    id: str
    location_id: str
    source: str
    temperature_c: float
    humidity: float
    rainfall_mm: float | None = None
    wind_speed_ms: float
    pressure_hpa: float
    visibility_km: float | None = None
    river_level_m: float | None = None
    river_level_available: bool = False
    storm_probability: float | None = None
    conditions: str
    observed_at: datetime
    provider_live: bool = False
    aoi_name: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    record_kind: str = "current_observation"
    units: dict[str, Any] | None = None
    data_provenance: dict[str, Any] | None = None


class WeatherForecastOut(BaseModel):
    id: str
    location_id: str
    source: str
    period_start: datetime
    period_end: datetime
    temperature_c: float
    rainfall_mm: float | None = None
    wind_speed_ms: float
    humidity: float | None = None
    pressure_hpa: float | None = None
    conditions: str
    record_kind: str = "forecast"
    units: dict[str, Any] | None = None


class WeatherHistoryPointOut(BaseModel):
    observed_at: datetime
    rainfall_mm: float | None = None
    temperature_c: float | None = None
    humidity: float | None = None
    wind_speed_ms: float | None = None
    river_level_m: float | None = None
    source: str
    record_kind: str = "historical_daily"
    spatial_resolution: str | None = None
    missing_fields: list[str] | None = None
    units: dict[str, Any] | None = None


class WeatherHistoryList(BaseModel):
    items: list[WeatherHistoryPointOut]
    total: int
    data_provenance: dict[str, Any] | None = None


class RainfallAnalysisOut(BaseModel):
    cumulative_mm: float
    intensity_mm_h: float
    anomaly: float
    short_term_risk: float
    label: str


class FloodRiskOut(BaseModel):
    flood_probability: float
    risk_score: float
    risk_level: str
    factors: list[FactorOut]
    recommended_action: str
    estimate_label: str
    data_provenance: dict[str, Any] | None = None
    is_official_warning: bool = False


class CycloneRiskOut(BaseModel):
    cyclone_risk: float
    severity: str
    affected_region: str
    recommended_action: str
    storm_probability: float
    estimate_label: str
    data_provenance: dict[str, Any] | None = None
    is_official_warning: bool = False


class WeatherAlertCandidateOut(BaseModel):
    id: str | None = None
    title: str
    severity: str
    category: str
    message: str
    issued_at: datetime
    location_name: str | None = None


class WeatherAlertsOut(BaseModel):
    items: list[WeatherAlertCandidateOut]
    total: int
    flood_probability: float
    cyclone_risk: float
    dispatch: str = "candidates stored only - no SMS/email sent"
    imd_status: str = ""
    imd_source_status: str = "UNAVAILABLE"


class WeatherForecastList(BaseModel):
    items: list[WeatherForecastOut]
    total: int
    provider_live: bool = False


class AlertOut(BaseModel):
    id: str
    title: str
    severity: str
    category: str
    message: str
    location_id: str | None
    issued_at: datetime
    alert_type: str = "weather"
    location_name: str = ""
    latitude: float = 12.9716
    longitude: float = 77.5946
    risk_score: float = 0
    expires_at: datetime | None = None
    status: str = "ACTIVE"
    recommended_action: str = ""
    source: str = "engine"
    acknowledged_at: datetime | None = None
    acknowledged_by: str = ""
    reason: str = ""
    disclaimer: str = "VisionGuard AI is a decision-support prototype. Alerts must be validated by authorized disaster-management personnel."
    official_warning: bool = False
    provenance_status: str = "UNKNOWN"
    alert_kind: str = "unverified"


class AlertList(BaseModel):
    items: list[AlertOut]
    total: int


class AlertGenerateRequest(BaseModel):
    location_id: str | None = None


class AlertAckRequest(BaseModel):
    actor: str = "ops.demo"


class RescueResourceOut(ORMModel):
    id: str
    name: str
    resource_type: str
    status: str
    personnel: int
    capacity: int = 0
    latitude: float = 12.9716
    longitude: float = 77.5946
    available_at: datetime | None = None
    assigned_incident: str | None = None
    location_id: str
    geojson: Any | None = None
    current_location: Any | None = None


class ResourceList(BaseModel):
    items: list[RescueResourceOut]
    total: int


class EvacuationCenterOut(ORMModel):
    id: str
    name: str
    capacity: int
    occupied: int
    status: str
    location_id: str
    geojson: Any | None = None


class EvacuationCenterList(BaseModel):
    items: list[EvacuationCenterOut]
    total: int


class HealthOut(BaseModel):
    status: str
    service: str
    environment: str
    use_mock_providers: bool
    data_mode: str = "DEMO DATA"


class SatelliteImageOut(BaseModel):
    id: str
    source: str
    acquisition_time: datetime
    latitude: float | None = None
    longitude: float | None = None
    bounding_box: Any | None = None
    resolution: str
    cloud_cover: float
    image_url: str
    thumbnail_url: str
    status: str
    metadata: Any | None = None
    title: str = ""
    provider: str = ""
    location_id: str = ""


class SatelliteImageList(BaseModel):
    items: list[SatelliteImageOut]
    total: int
    query: Any | None = None


class AnalyzeRequest(BaseModel):
    image_id: str
    analysis_type: str = "flood"


class CompareRequest(BaseModel):
    before_image: str
    after_image: str


class SatelliteAnalysisOut(BaseModel):
    id: str
    satellite_image_id: str
    model_name: str
    analysis_type: str
    summary: str
    confidence: float
    result_geojson: Any | None = None
    metrics: Any | None = None
    created_at: datetime
    estimate_label: str = "Prototype satellite analysis"


class DetectionOut(BaseModel):
    label: str
    confidence: float
    bbox: list[float]
    severity: str
    specialized: bool = False


class VisionResultOut(BaseModel):
    image_id: str
    model_name: str
    backend: str
    overall_severity: str
    processing_time_ms: float
    detections: list[DetectionOut]
    incident: Any | None = None
    notes: str = ""
    annotated_url: str = ""
    gpu_required: bool = False


class FloodAnalyzeRequest(BaseModel):
    scene_kind: str = "flood"
    population: int | None = None
    latitude: float | None = None
    longitude: float | None = None
    bbox_pad_deg: float | None = None


class AoiSelectRequest(BaseModel):
    district: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    bbox_pad_deg: float | None = None
    bbox: list[float] | None = None
    aoi_name: str | None = None


class FloodEventOut(BaseModel):
    id: str
    model_name: str
    scene_kind: str
    flooded_area: float
    flood_percentage: float
    severity: str
    confidence: float
    boundary_geojson: Any | None = None
    heatmap_geojson: Any | None = None
    affected_population: int
    affected_roads: int
    affected_buildings: int
    notes: str = ""
    created_at: datetime
    estimate_label: str = "Prototype flood extent (OpenCV/NumPy demo, not a trained U-Net/DeepLab)"
    # Before/after change fields (REAL Sentinel change path; optional for older rows).
    before_water_area_km2: float | None = None
    after_water_area_km2: float | None = None
    newly_flooded_area_km2: float | None = None
    newly_flooded_percentage: float | None = None
    percentage_change: float | None = None
    before_image_id: str | None = None
    after_image_id: str | None = None
    before_stac_id: str | None = None
    after_stac_id: str | None = None
    before_date: str | None = None
    after_date: str | None = None
    before_cloud: float | None = None
    after_cloud: float | None = None
    before_preview_url: str | None = None
    after_preview_url: str | None = None
    before_water_geojson: Any | None = None
    after_water_geojson: Any | None = None
    newly_flooded_geojson: Any | None = None
    change_metrics: dict[str, Any] | None = None
    analysis_status: str | None = None
    processing_method: str | None = None
    spatial_resolution: str | None = None
    validated_flood_boundary: bool = False
    impact_stats_available: bool = False


class FloodEventList(BaseModel):
    items: list[FloodEventOut]
    total: int


class DamageAnalyzeRequest(BaseModel):
    before_kind: str = "flood_before"
    after_kind: str = "flood"


class DamageAssessmentOut(BaseModel):
    id: str
    model_name: str
    before_kind: str
    after_kind: str
    report: Any | None = None
    overlay_geojson: Any | None = None
    created_at: datetime
    estimate_label: str = "Prototype damage assessment (change detection, not a trained model)"
    pdf_available: bool = False


class DamageAssessmentList(BaseModel):
    items: list[DamageAssessmentOut]
    total: int


class AllocateRequest(BaseModel):
    resource_id: str
    incident_id: str


class RescuePlanRequest(BaseModel):
    disaster_id: str | None = None


class RescueDecisionRequest(BaseModel):
    action: str
    notes: str = ""


class RescuePriorityOut(BaseModel):
    id: str
    disaster_id: str
    title: str
    priority: int
    people_affected: int
    status: str
    score: float = 0
    level: str = "MEDIUM"
    factors: Any | None = None
    geojson: Any | None = None
    estimate_label: str = "Prototype rescue priority (not guaranteed optimal)"


class RescuePriorityList(BaseModel):
    items: list[RescuePriorityOut]
    total: int


class RescuePlanOut(BaseModel):
    id: str
    disaster_id: str
    priority_id: str | None = None
    decision: str
    override_notes: str = ""
    plan: Any | None = None
    created_at: datetime
    estimate_label: str = "Prototype decision-support recommendation — not a guaranteed optimal allocation"


class ReportRequest(BaseModel):
    kind: str = "incident"
    disaster_id: str | None = None


class AuditLogOut(BaseModel):
    id: str
    action: str
    entity_type: str
    entity_id: str
    details: str = ""
    created_at: datetime


class AuditLogList(BaseModel):
    items: list[AuditLogOut]
    total: int
