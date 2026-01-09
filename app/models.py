from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class DownloadRequest(BaseModel):
    url: str
    kind: str = Field("audio", description="audio or video")
    resolution: Optional[str] = Field(None, description="e.g. 360p or highest for video")
    bitrate: Optional[str] = Field(None, description="audio bitrate, e.g. 192 or 320")


class DownloadResult(BaseModel):
    title: str
    filepath: str
    size_mb: float
    duration_minutes: float
    downloaded_at: datetime
    url: str
    kind: str


class StatsResponse(BaseModel):
    total_size_mb: float
    total_items: float


class PlaylistDownloadRequest(BaseModel):
    url: str
    kind: str = Field("audio", description="audio or video")
    resolution: Optional[str] = Field(None, description="resolution for video; highest by default")
    bitrate: Optional[str] = Field(None, description="audio bitrate, e.g. 192 or 320")


class PlaylistItem(BaseModel):
    title: str
    filepath: str
    size_mb: float
    duration_minutes: float
    downloaded_at: datetime
    url: str
    kind: str


class PlaylistDownloadResult(BaseModel):
    count: int
    items: list[PlaylistItem]
    playlist_title: str | None = None
