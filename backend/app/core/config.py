from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Always prefer backend/.env (this file lives at backend/app/core/config.py).
_BACKEND_DIR = Path(__file__).resolve().parents[2]
_ENV_FILES = tuple(
    str(path)
    for path in (_BACKEND_DIR / ".env", Path.cwd() / ".env")
    if path.is_file()
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILES or ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "VisionGuard AI"
    environment: str = "development"
    api_v1_prefix: str = "/api/v1"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    database_url: str = "sqlite:///./visionguard.db"
    # Default Real Data Mode; set USE_MOCK_PROVIDERS=true only for explicit Demo Mode.
    use_mock_providers: bool = False
    openweather_api_key: str | None = None
    openweather_query: str = "Bengaluru,IN"
    nasa_power_base_url: str = "https://power.larc.nasa.gov/api/temporal/daily/point"
    nasa_power_enabled: bool = True
    imd_api_base_url: str = "https://api.imd.gov.in/api/v1"
    imd_api_key: str | None = None
    imd_station_id: str = "43314"
    copernicus_client_id: str | None = None
    copernicus_client_secret: str | None = None
    copernicus_stac_url: str = "https://stac.dataspace.copernicus.eu/v1"
    copernicus_token_url: str = (
        "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
    )
    copernicus_max_cloud: float = 40.0
    copernicus_lookback_days: int = 60
    satellite_min_start_date: str = "2026-05-01"
    # Primary live AOI: Karnataka / Bengaluru, India (env still DEMO_LATITUDE / DEMO_LONGITUDE).
    aoi_name: str = "Karnataka / Bengaluru (India)"
    aoi_state: str = "Karnataka"
    aoi_country: str = "India"
    demo_latitude: float = 12.9716
    demo_longitude: float = 77.5946
    log_level: str = "INFO"
    vision_storage_dir: str = "./storage/vision"
    yolo_weights_path: str | None = None
    max_upload_mb: int = 8
    enable_real_email: bool = False
    enable_real_sms: bool = False
    enable_real_push: bool = False
    smtp_host: str | None = None
    sms_api_key: str | None = None
    push_api_key: str | None = None
    # GIS / OpenStreetMap Overpass (reference data — STATIC_EXTERNAL, not live incidents)
    gis_overpass_enabled: bool = True
    gis_overpass_url: str = "https://overpass-api.de/api/interpreter"
    gis_cache_ttl_sec: int = 3600
    gis_bbox_pad_deg: float = 0.06

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
