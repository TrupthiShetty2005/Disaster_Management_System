from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
_ENV_FILES = tuple(str(p) for p in (BACKEND_DIR / ".env", Path.cwd() / ".env") if p.is_file())


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_ENV_FILES or ".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "VisionGuard AI — Karnataka"
    environment: str = "development"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    database_url: str = f"sqlite:///{BACKEND_DIR / 'visionguard.db'}"
    log_level: str = "INFO"
    cache_dir: str = str(BACKEND_DIR / "storage" / "cache")
    storage_dir: str = str(BACKEND_DIR / "storage")

    # OpenWeather (current conditions + 5-day/3-hour forecast)
    openweather_api_key: str | None = None
    # NASA FIRMS: public regional CSVs work without a key; a MAP_KEY enables the area API.
    firms_map_key: str | None = None
    # Microsoft Planetary Computer STAC (Sentinel-2 L2A, Sentinel-1 RTC); anonymous SAS tokens.
    planetary_stac_url: str = "https://planetarycomputer.microsoft.com/api/stac/v1"
    planetary_sas_url: str = "https://planetarycomputer.microsoft.com/api/sas/v1/token"
    overpass_url: str = "https://overpass-api.de/api/interpreter"
    osrm_url: str = "https://router.project-osrm.org"

    # Karnataka defaults (state-wide view; districts are selectable in the UI).
    default_latitude: float = 12.9716
    default_longitude: float = 77.5946

    satellite_max_cloud: float = 30.0
    satellite_max_pixels: int = 768
    max_upload_mb: int = 8
    yolo_model: str = "yolov8n.pt"
    max_video_upload_mb: int = 40
    video_max_seconds: float = 20
    # Download + run the openly licensed benchmark gallery (vision_gallery.json) in the background.
    vision_gallery_autobuild: bool = True
    refresh_interval_min: int = 30

    # Indicative loss model (INR). Exposure counts are measured; these unit costs and damage ratios
    # are planning assumptions and are returned alongside every estimate.
    loss_building_inr: float = 300_000
    loss_road_major_inr_per_km: float = 10_000_000
    loss_road_minor_inr_per_km: float = 2_500_000
    loss_rail_inr_per_km: float = 20_000_000
    loss_power_line_inr_per_km: float = 3_000_000
    damage_ratio_flood: float = 0.25
    damage_ratio_fire: float = 0.5

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
