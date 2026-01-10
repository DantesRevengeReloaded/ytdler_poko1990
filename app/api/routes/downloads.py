import asyncio
from fastapi import APIRouter, HTTPException
import logging

from uuid import uuid4

from app.models import (
    DownloadRequest,
    DownloadResult,
    PlaylistDownloadRequest,
    PlaylistDownloadResult,
    ProgressSnapshot,
)
from app.services.downloads import download, download_playlist_async, get_progress

router = APIRouter(prefix="/api/v1/downloads", tags=["downloads"])


@router.post("/", response_model=DownloadResult)
async def create_download(payload: DownloadRequest):
    logging.info(f"Received download request: kind={payload.kind}, url={payload.url}")
    job_id = payload.job_id or str(uuid4())
    try:
        result = await download(payload.kind, payload.url, payload.resolution, payload.bitrate, job_id)
        result["job_id"] = job_id
        logging.info(f"Download completed successfully")
        return DownloadResult(**result)
    except Exception as exc:  # broad so we surface errors
        logging.error(f"Download failed: {exc}")
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/playlist", response_model=PlaylistDownloadResult)
async def create_playlist_download(payload: PlaylistDownloadRequest):
    logging.info(f"Received playlist download request: kind={payload.kind}, url={payload.url}")
    job_id = payload.job_id or str(uuid4())
    try:
        result = await download_playlist_async(payload.kind, payload.url, payload.resolution, payload.bitrate, job_id)
        result["job_id"] = job_id
        logging.info(f"Playlist download completed successfully")
        return PlaylistDownloadResult(**result)
    except Exception as exc:
        logging.error(f"Playlist download failed: {exc}")
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/progress/{job_id}", response_model=ProgressSnapshot)
async def fetch_progress(job_id: str):
    snapshot = get_progress(job_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail="Job not found")
    total = snapshot.get("total") or 0
    completed = snapshot.get("completed") or 0
    progress_percent = None
    if total:
        progress_percent = min(100.0, max(0.0, (completed / total) * 100))
    return ProgressSnapshot(
        job_id=job_id,
        job_type=snapshot.get("job_type", "unknown"),
        phase=snapshot.get("phase", "unknown"),
        message=snapshot.get("message", ""),
        total=total or None,
        completed=completed or None,
        progress_percent=progress_percent,
        started_at=snapshot.get("started_at"),
        updated_at=snapshot.get("updated_at"),
        error=snapshot.get("error"),
        playlist_title=snapshot.get("playlist_title"),
    )
