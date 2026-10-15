from datetime import datetime
from typing import Protocol

from pydantic import BaseModel, Field


class SatelliteScene(BaseModel):
    id: str
    source: str
    acquisition_time: datetime
    latitude: float | None = None
    longitude: float | None = None
    bounding_box: dict | None = None
    resolution: str = "10m"
    cloud_cover: float = 0
    image_url: str = ""
    thumbnail_url: str = ""
    status: str = "ready"
    metadata: dict = Field(default_factory=dict)
    location_id: str = ""
    scene_kind: str = "normal"
    title: str = ""


class SatelliteProvider(Protocol):
    name: str
    live: bool

    def list_scenes(self, start=None, end=None, max_cloud=None) -> list[SatelliteScene]: ...

    def get_scene(self, scene_id: str) -> SatelliteScene | None: ...

    def scene_kind(self, scene_id: str) -> str: ...
