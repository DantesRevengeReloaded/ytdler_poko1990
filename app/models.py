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


class SpotifyPlaylistRequest(BaseModel):
    url: str = Field(..., description="Spotify playlist/album/artist URL, URI, or raw ID")


class SpotifyTrack(BaseModel):
    title: str
    artist: str
    album: str | None = None
    spotify_url: str | None = None


class SpotifyPlaylistResponse(BaseModel):
    playlist_title: str
    description: str | None = None
    owner: str | None = None
    track_count: int
    tracks: list[SpotifyTrack]
    source_type: str = Field("playlist", description="playlist | album | artist")


class SpotifyMirrorRequest(BaseModel):
    url: str = Field(..., description="Spotify playlist/album/artist URL or URI")
    bitrate: str | None = Field("192", description="MP3 bitrate for mirrored downloads")
    job_id: str | None = Field(None, description="Client-supplied job id for progress tracking")


class SpotifyMirrorItem(BaseModel):
    title: str
    artist: str
    query: str
    filepath: str | None = None
    status: str
    error: str | None = None


class SpotifyMirrorResponse(BaseModel):
    playlist_title: str
    source_type: str
    track_count: int
    downloaded: int
    items: list[SpotifyMirrorItem]
    job_id: str
