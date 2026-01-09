import asyncio
from fastapi import APIRouter, HTTPException
import logging

from app.models import (
    DownloadRequest,
    DownloadResult,
    PlaylistDownloadRequest,
    PlaylistDownloadResult,
)
from app.services.downloads import download, download_playlist_async

router = APIRouter(prefix="/api/v1/downloads", tags=["downloads"])


@router.post("/", response_model=DownloadResult)
async def create_download(payload: DownloadRequest):
    logging.info(f"Received download request: kind={payload.kind}, url={payload.url}")
    try:
        result = await download(payload.kind, payload.url, payload.resolution, payload.bitrate)
        logging.info(f"Download completed successfully")
        return DownloadResult(**result)
    except Exception as exc:  # broad so we surface errors
        logging.error(f"Download failed: {exc}")
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/playlist", response_model=PlaylistDownloadResult)
async def create_playlist_download(payload: PlaylistDownloadRequest):
    logging.info(f"Received playlist download request: kind={payload.kind}, url={payload.url}")
    try:
        result = await download_playlist_async(payload.kind, payload.url, payload.resolution, payload.bitrate)
        logging.info(f"Playlist download completed successfully")
        return PlaylistDownloadResult(**result)
    except Exception as exc:
        logging.error(f"Playlist download failed: {exc}")
        raise HTTPException(status_code=400, detail=str(exc))
