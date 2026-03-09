import asyncio
import logging

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse

from app.models import SpotifyHistoryItem, SpotifyHistoryResponse, SpotifyMirrorRequest, SpotifyMirrorResponse, SpotifyPlaylistRequest, SpotifyPlaylistResponse
from app.services import spotify as spotify_service
from app.services import db_manager

router = APIRouter(prefix="/api/v1/spotify", tags=["spotify"])


@router.get("/auth/login")
async def spotify_auth_login():
    """Redirect user to Spotify OAuth authorization page."""
    try:
        url = spotify_service.get_oauth_url()
        return RedirectResponse(url)
    except spotify_service.SpotifyConfigError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/auth/callback")
async def spotify_auth_callback(code: str | None = None, error: str | None = None):
    """Handle Spotify OAuth callback and store user token."""
    if error:
        raise HTTPException(status_code=400, detail=f"Spotify auth denied: {error}")
    if not code:
        raise HTTPException(status_code=400, detail="Missing OAuth code")
    try:
        await asyncio.to_thread(spotify_service.handle_oauth_callback, code)
        return {"status": "ok", "message": "Spotify account connected successfully. You can now mirror any public playlist."}
    except spotify_service.SpotifyAPIError as exc:
        logging.error(f"Spotify OAuth callback error: {exc}")
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/auth/status")
async def spotify_auth_status():
    """Return Spotify OAuth connection status."""
    return spotify_service.get_auth_status()


@router.post("/playlist", response_model=SpotifyPlaylistResponse)
async def fetch_spotify_playlist(payload: SpotifyPlaylistRequest):
    logging.info(f"Received Spotify playlist request for url={payload.url}")
    try:
        data = await asyncio.to_thread(spotify_service.get_playlist_details, payload.url)
        return SpotifyPlaylistResponse(**data)
    except spotify_service.SpotifyConfigError as exc:
        logging.error(f"Spotify config error: {exc}")
        raise HTTPException(status_code=400, detail=str(exc))
    except spotify_service.SpotifyAPIError as exc:
        logging.error(f"Spotify API error: {exc}")
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:  # noqa: BLE001
        logging.error(f"Unexpected Spotify error: {exc}")
        raise HTTPException(status_code=500, detail="Unexpected Spotify error")


@router.get("/history", response_model=SpotifyHistoryResponse)
async def get_spotify_history(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    items = db_manager.get_spotify_history(limit=limit, offset=offset)
    total = db_manager.get_spotify_history_count()
    return SpotifyHistoryResponse(
        items=[SpotifyHistoryItem(**item) for item in items],
        total=total,
    )


@router.post("/mirror", response_model=SpotifyMirrorResponse)
async def mirror_spotify_playlist(payload: SpotifyMirrorRequest):
    logging.info(f"Received Spotify mirror request for url={payload.url}")
    try:
        data = await asyncio.to_thread(spotify_service.mirror_to_youtube, payload.url, payload.bitrate, payload.job_id)
        return SpotifyMirrorResponse(**data)
    except spotify_service.SpotifyConfigError as exc:
        logging.error(f"Spotify config error: {exc}")
        raise HTTPException(status_code=400, detail=str(exc))
    except spotify_service.SpotifyAPIError as exc:
        logging.error(f"Spotify API error: {exc}")
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:  # noqa: BLE001
        logging.error(f"Unexpected Spotify mirror error: {exc}")
        raise HTTPException(status_code=500, detail="Unexpected Spotify mirror error")
