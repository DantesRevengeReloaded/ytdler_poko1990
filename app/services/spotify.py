import base64
import logging
import os
import re
import time
from datetime import datetime
from typing import Dict, List, Tuple

import requests

from app.core.config import get_settings
from app.services import db_manager
from app.services.downloads import _start_progress, _set_progress, _finish_progress

logger = logging.getLogger(__name__)

_TOKEN_URL = "https://accounts.spotify.com/api/token"
_API_BASE = "https://api.spotify.com/v1"
_TOKEN_CACHE: Dict[str, float | str | None] = {"access_token": None, "expires_at": 0.0}


class SpotifyConfigError(Exception):
    """Raised when Spotify credentials are missing."""


class SpotifyAPIError(Exception):
    """Raised when Spotify API responds with an error."""


def _get_client_creds() -> Tuple[str, str]:
    settings = get_settings()
    cid = settings.spotify_client_id
    secret = settings.spotify_client_secret
    if not cid or not secret:
        raise SpotifyConfigError("Spotify client id/secret not configured. Set POKODLER_SPOTIFY_CLIENT_ID and POKODLER_SPOTIFY_CLIENT_SECRET.")
    return cid, secret


def _request_token() -> str:
    cid, secret = _get_client_creds()
    auth_header = base64.b64encode(f"{cid}:{secret}".encode()).decode()
    resp = requests.post(
        _TOKEN_URL,
        data={"grant_type": "client_credentials"},
        headers={"Authorization": f"Basic {auth_header}"},
        timeout=10,
    )
    if resp.status_code != 200:
        raise SpotifyAPIError(f"Spotify auth failed ({resp.status_code}): {resp.text}")
    data = resp.json()
    token = data.get("access_token")
    expires_in = data.get("expires_in", 3600)
    if not token:
        raise SpotifyAPIError("Spotify auth failed: no access token returned")
    _TOKEN_CACHE["access_token"] = token
    _TOKEN_CACHE["expires_at"] = time.time() + expires_in - 30  # refresh slightly early
    logger.info("Fetched new Spotify access token")
    return token


def _get_token() -> str:
    cached = _TOKEN_CACHE.get("access_token")
    expires_at = _TOKEN_CACHE.get("expires_at", 0)
    if cached and time.time() < float(expires_at):
        return cached  # type: ignore
    return _request_token()


def _authorized_headers(token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Accept": "application/json"}


def extract_resource(url: str) -> Tuple[str, str]:
    """Return (resource_type, id) where resource_type in {playlist, album, artist}."""
    if not url:
        raise SpotifyAPIError("Spotify URL is required")
    url = url.strip()

    # URI forms
    for kind in ("playlist", "album", "artist"):
        m = re.search(rf"spotify:{kind}:([A-Za-z0-9]+)", url)
        if m:
            return kind, m.group(1)

    # Web URLs
    for kind in ("playlist", "album", "artist"):
        m = re.search(rf"{kind}/([A-Za-z0-9]+)", url)
        if m:
            return kind, m.group(1)

    # Raw ID fallback defaults to playlist for compatibility
    if re.match(r"^[A-Za-z0-9]{16,}$", url):
        return "playlist", url

    raise SpotifyAPIError("Could not parse Spotify ID from URL")


def _sanitize(name: str) -> str:
    clean = "".join(c for c in name if c.isalnum() or c in (" ", "-", "_"))
    clean = clean.strip().replace(" ", "_")
    return clean or "playlist"


def _fetch_playlist_meta(playlist_id: str, token: str) -> Dict:
    url = f"{_API_BASE}/playlists/{playlist_id}"
    params = {"market": "US", "fields": "name,description,owner(display_name),tracks(total)"}
    resp = requests.get(url, headers=_authorized_headers(token), params=params, timeout=10)
    if resp.status_code == 401:
        _TOKEN_CACHE["access_token"] = None
        token = _request_token()
        resp = requests.get(url, headers=_authorized_headers(token), params=params, timeout=10)
    if resp.status_code != 200:
        raise SpotifyAPIError(f"Spotify playlist fetch failed ({resp.status_code}): {resp.text}")
    return resp.json()


def _fetch_album_meta(album_id: str, token: str) -> Dict:
    url = f"{_API_BASE}/albums/{album_id}"
    params = {"market": "US"}
    resp = requests.get(url, headers=_authorized_headers(token), params=params, timeout=10)
    if resp.status_code == 401:
        _TOKEN_CACHE["access_token"] = None
        token = _request_token()
        resp = requests.get(url, headers=_authorized_headers(token), params=params, timeout=10)
    if resp.status_code != 200:
        raise SpotifyAPIError(f"Spotify album fetch failed ({resp.status_code}): {resp.text}")
    return resp.json()


def _fetch_playlist_tracks(playlist_id: str, token: str, max_items: int = 200) -> List[Dict]:
    tracks: List[Dict] = []
    offset = 0
    limit = 100
    url = f"{_API_BASE}/playlists/{playlist_id}/tracks"
    headers = _authorized_headers(token)
    while True:
        params = {"market": "US", "limit": limit, "offset": offset}
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        if resp.status_code == 401:
            _TOKEN_CACHE["access_token"] = None
            token = _request_token()
            headers = _authorized_headers(token)
            resp = requests.get(url, headers=headers, params=params, timeout=10)
        if resp.status_code != 200:
            raise SpotifyAPIError(f"Spotify tracks fetch failed ({resp.status_code}): {resp.text}")
        data = resp.json()
        items = data.get("items", [])
        for item in items:
            track = item.get("track") or {}
            if not track:
                continue
            name = track.get("name", "Unknown")
            artists = track.get("artists") or []
            artist_names = ", ".join([a.get("name") for a in artists if a]) or "Unknown"
            album_name = (track.get("album") or {}).get("name")
            spotify_url = (track.get("external_urls") or {}).get("spotify")
            tracks.append(
                {
                    "title": name,
                    "artist": artist_names,
                    "album": album_name,
                    "spotify_url": spotify_url,
                }
            )
            if len(tracks) >= max_items:
                return tracks
        if not data.get("next"):
            break
        offset += limit
    return tracks


def _fetch_album_tracks(album_id: str, token: str, max_items: int = 200) -> List[Dict]:
    tracks: List[Dict] = []
    offset = 0
    limit = 50
    url = f"{_API_BASE}/albums/{album_id}/tracks"
    headers = _authorized_headers(token)
    while True:
        params = {"market": "US", "limit": limit, "offset": offset}
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        if resp.status_code == 401:
            _TOKEN_CACHE["access_token"] = None
            token = _request_token()
            headers = _authorized_headers(token)
            resp = requests.get(url, headers=headers, params=params, timeout=10)
        if resp.status_code != 200:
            raise SpotifyAPIError(f"Spotify album tracks fetch failed ({resp.status_code}): {resp.text}")
        data = resp.json()
        items = data.get("items", [])
        for item in items:
            name = item.get("name", "Unknown")
            artists = item.get("artists") or []
            artist_names = ", ".join([a.get("name") for a in artists if a]) or "Unknown"
            spotify_url = (item.get("external_urls") or {}).get("spotify")
            tracks.append(
                {
                    "title": name,
                    "artist": artist_names,
                    "album": None,
                    "spotify_url": spotify_url,
                }
            )
            if len(tracks) >= max_items:
                return tracks
        if not data.get("next"):
            break
        offset += limit
    return tracks


def _fetch_artist_top_tracks(artist_id: str, token: str, max_items: int = 50) -> List[Dict]:
    url = f"{_API_BASE}/artists/{artist_id}/top-tracks"
    params = {"market": "US"}
    resp = requests.get(url, headers=_authorized_headers(token), params=params, timeout=10)
    if resp.status_code == 401:
        _TOKEN_CACHE["access_token"] = None
        token = _request_token()
        resp = requests.get(url, headers=_authorized_headers(token), params=params, timeout=10)
    if resp.status_code != 200:
        raise SpotifyAPIError(f"Spotify artist tracks fetch failed ({resp.status_code}): {resp.text}")
    data = resp.json()
    items = data.get("tracks", [])[:max_items]
    tracks: List[Dict] = []
    for item in items:
        name = item.get("name", "Unknown")
        artists = item.get("artists") or []
        artist_names = ", ".join([a.get("name") for a in artists if a]) or "Unknown"
        album_name = (item.get("album") or {}).get("name")
        spotify_url = (item.get("external_urls") or {}).get("spotify")
        tracks.append(
            {
                "title": name,
                "artist": artist_names,
                "album": album_name,
                "spotify_url": spotify_url,
            }
        )
    return tracks


def get_playlist_details(url: str) -> Dict:
    resource_type, resource_id = extract_resource(url)
    token = _get_token()

    if resource_type == "playlist":
        meta = _fetch_playlist_meta(resource_id, token)
        tracks = _fetch_playlist_tracks(resource_id, token)
        return {
            "playlist_title": meta.get("name", "Spotify playlist"),
            "description": meta.get("description"),
            "owner": (meta.get("owner") or {}).get("display_name"),
            "track_count": meta.get("tracks", {}).get("total", len(tracks)),
            "tracks": tracks,
            "source_type": "playlist",
        }

    if resource_type == "album":
        meta = _fetch_album_meta(resource_id, token)
        tracks = _fetch_album_tracks(resource_id, token)
        artist_names = ", ".join([a.get("name") for a in meta.get("artists", []) if a]) or None
        return {
            "playlist_title": meta.get("name", "Spotify album"),
            "description": meta.get("label"),
            "owner": artist_names,
            "track_count": meta.get("total_tracks", len(tracks)),
            "tracks": tracks,
            "source_type": "album",
        }

    if resource_type == "artist":
        # Use top tracks for artists to provide a meaningful list.
        tracks = _fetch_artist_top_tracks(resource_id, token)
        artist_meta = requests.get(f"{_API_BASE}/artists/{resource_id}", headers=_authorized_headers(token), timeout=10)
        if artist_meta.status_code == 401:
            _TOKEN_CACHE["access_token"] = None
            token = _request_token()
            artist_meta = requests.get(f"{_API_BASE}/artists/{resource_id}", headers=_authorized_headers(token), timeout=10)
        if artist_meta.status_code != 200:
            raise SpotifyAPIError(f"Spotify artist fetch failed ({artist_meta.status_code}): {artist_meta.text}")
        meta = artist_meta.json()
        return {
            "playlist_title": meta.get("name", "Spotify artist"),
            "description": None,
            "owner": meta.get("name"),
            "track_count": len(tracks),
            "tracks": tracks,
            "source_type": "artist",
        }

    raise SpotifyAPIError("Unsupported Spotify resource type")


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _yt_audio_opts(download_dir: str, bitrate: str | None) -> Dict:
    return {
        "outtmpl": os.path.join(download_dir, "%(title)s.%(ext)s"),
        "quiet": True,
        "noplaylist": True,
        "format": "bestaudio/best",
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": bitrate or "192",
            }
        ],
    }


def mirror_to_youtube(url: str, bitrate: str | None = "192", job_id: str | None = None) -> Dict:
    settings = get_settings()
    playlist = get_playlist_details(url)
    playlist_title = playlist.get("playlist_title", "spotify_playlist")
    source_type = playlist.get("source_type", "playlist")
    tracks = playlist.get("tracks", [])
    total_tracks = len(tracks)

    base_dir = os.path.join(settings.download_dir, "spotify_playlists")
    _ensure_dir(base_dir)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder_name = f"{_sanitize(playlist_title)}_{timestamp}"
    playlist_dir = os.path.join(base_dir, folder_name)
    _ensure_dir(playlist_dir)

    if job_id:
        _start_progress(job_id, job_type="spotify", message="Preparing Spotify mirror", total=total_tracks or None)
        _set_progress(
            job_id,
            phase="queued",
            message=f"{playlist_title}: Total {total_tracks} tracks",
            total=total_tracks or None,
            completed=0,
            playlist_title=playlist_title,
            updated_at=datetime.utcnow(),
        )

    items = []
    downloaded = 0
    manifest_lines = []
    for idx, track in enumerate(tracks, start=1):
        manifest_lines.append(f"{idx:03d}. {track.get('title','Unknown')} — {track.get('artist','Unknown')}")
    manifest_path = os.path.join(playlist_dir, "tracks_manifest.txt")
    with open(manifest_path, "w", encoding="utf-8") as f:
        f.write("\n".join(manifest_lines))
    for idx, track in enumerate(tracks, start=1):
        title = track.get("title", "Unknown")
        artist = track.get("artist", "Unknown")
        query = f"{title} {artist}".strip()
        opts = _yt_audio_opts(playlist_dir, bitrate)
        # Prefix filenames with index to preserve order
        opts["outtmpl"] = os.path.join(playlist_dir, f"{idx:03d}_%(title)s.%(ext)s")
        opts["default_search"] = "auto"  # allows direct URL or search
        try:
            import yt_dlp  # local import to avoid global dependency at module load

            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(f"ytsearch1:{query}", download=True)
                # ytsearch returns a playlist-like dict with entries
                entry = None
                if info.get("entries"):
                    entry = info["entries"][0]
                if not entry:
                    raise SpotifyAPIError(f"No search result for {query}")
                filepath = ydl.prepare_filename(entry)
                if not filepath.endswith(".mp3"):
                    base, _ = os.path.splitext(filepath)
                    filepath = base + ".mp3"
                size_mb = os.path.getsize(filepath) / (1024 * 1024) if os.path.exists(filepath) else 0
                downloaded_at = datetime.utcnow()
                db_manager.store_spotify_mirror_entry(
                    playlist_title=playlist_title,
                    source_type=source_type,
                    track_title=entry.get("title", title),
                    artist=artist,
                    query=query,
                    filepath=filepath,
                    status="downloaded",
                    error=None,
                    downloaded_at=downloaded_at,
                )
                items.append(
                    {
                        "title": entry.get("title", title),
                        "artist": artist,
                        "query": query,
                        "filepath": filepath,
                        "status": "downloaded",
                        "error": None,
                    }
                )
                downloaded += 1
                if job_id:
                    _set_progress(
                        job_id,
                        phase="downloading",
                        message=f"{playlist_title}: Total {total_tracks} tracks {idx}/{total_tracks} downloaded",
                        total=total_tracks or None,
                        completed=idx,
                        playlist_title=playlist_title,
                        updated_at=datetime.utcnow(),
                    )
        except Exception as exc:  # noqa: BLE001
            db_manager.store_spotify_mirror_entry(
                playlist_title=playlist_title,
                source_type=source_type,
                track_title=title,
                artist=artist,
                query=query,
                filepath=None,
                status="failed",
                error=str(exc),
                downloaded_at=datetime.utcnow(),
            )
            items.append(
                {
                    "title": title,
                    "artist": artist,
                    "query": query,
                    "filepath": None,
                    "status": "failed",
                    "error": str(exc),
                }
            )
            if job_id:
                _set_progress(
                    job_id,
                    phase="downloading",
                    message=f"{playlist_title}: Total {total_tracks} tracks {idx}/{total_tracks} processed",
                    total=total_tracks or None,
                    completed=idx,
                    playlist_title=playlist_title,
                    updated_at=datetime.utcnow(),
                    error=str(exc),
                )

    downloaded = sum(1 for item in items if item.get("status") == "downloaded")

    if job_id:
        _finish_progress(job_id, message=f"{playlist_title}: Downloaded {downloaded}/{total_tracks} tracks")

    return {
        "playlist_title": playlist_title,
        "source_type": source_type,
        "track_count": total_tracks,
        "downloaded": downloaded,
        "items": items,
        "manifest_path": manifest_path,
        "job_id": job_id or "",
    }
