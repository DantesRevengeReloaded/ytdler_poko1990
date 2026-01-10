import asyncio
import logging

from fastapi import APIRouter, HTTPException

from app.models import SpotifyMirrorRequest, SpotifyMirrorResponse, SpotifyPlaylistRequest, SpotifyPlaylistResponse
from app.services import spotify as spotify_service

router = APIRouter(prefix="/api/v1/spotify", tags=["spotify"])


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


@router.post("/mirror", response_model=SpotifyMirrorResponse)
async def mirror_spotify_playlist(payload: SpotifyMirrorRequest):
    logging.info(f"Received Spotify mirror request for url={payload.url}")
    try:
        data = await asyncio.to_thread(spotify_service.mirror_to_youtube, payload.url, payload.bitrate)
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
