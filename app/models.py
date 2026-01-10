from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class DownloadRequest(BaseModel):
    url: str
    kind: str = Field("audio", description="audio or video")
    resolution: Optional[str] = Field(None, description="e.g. 360p or highest for video")
    bitrate: Optional[str] = Field(None, description="audio bitrate, e.g. 192 or 320")
    job_id: Optional[str] = Field(None, description="Client-supplied job id for progress tracking")


class DownloadResult(BaseModel):
    title: str
    filepath: str
    size_mb: float
    duration_minutes: float
    downloaded_at: datetime
    url: str
    kind: str
    job_id: str
    duration_seconds: float


class StatsResponse(BaseModel):
    total_size_mb: float
    total_items: float


class PlaylistDownloadRequest(BaseModel):
    url: str
    kind: str = Field("audio", description="audio or video")
    resolution: Optional[str] = Field(None, description="resolution for video; highest by default")
    bitrate: Optional[str] = Field(None, description="audio bitrate, e.g. 192 or 320")
    job_id: Optional[str] = Field(None, description="Client-supplied job id for progress tracking")


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
    job_id: str
    duration_seconds: float


class ProgressSnapshot(BaseModel):
    job_id: str
    job_type: str
    phase: str
    message: str
    total: int | None = None
    completed: int | None = None
    progress_percent: float | None = None
    started_at: datetime | None = None
    updated_at: datetime | None = None
    error: str | None = None
    playlist_title: str | None = None
