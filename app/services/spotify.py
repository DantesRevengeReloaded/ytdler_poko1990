import base64
import json
import logging
import os
import re
import time
import urllib.parse
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import requests

from app.core.config import get_settings
from app.services import db_manager
from app.services.downloads import _start_progress, _set_progress, _finish_progress, _write_id3_tags

logger = logging.getLogger(__name__)

_TOKEN_URL = "https://accounts.spotify.com/api/token"
_AUTH_URL = "https://accounts.spotify.com/authorize"
_API_BASE = "https://api.spotify.com/v1"

# Client credentials token cache
_TOKEN_CACHE: Dict[str, float | str | None] = {"access_token": None, "expires_at": 0.0}

# User OAuth token (Authorization Code flow) — takes priority when set
_USER_TOKEN: Dict[str, Optional[str | float]] = {
    "access_token": None,
    "refresh_token": None,
    "expires_at": 0.0,
}

_OAUTH_SCOPES = "playlist-read-private playlist-read-collaborative"
_TOKEN_FILE = os.path.join(os.path.dirname(__file__), ".spotify_user_token.json")

# sp_dc web player token cache (bypasses editorial playlist restrictions)
_SP_DC_TOKEN: Dict[str, Optional[str | float]] = {"access_token": None, "expires_at": 0.0}


def _get_sp_dc_token() -> Optional[str]:
    """Get a Spotify web player token using the sp_dc cookie. Returns None if sp_dc not configured."""
    settings = get_settings()
    sp_dc = settings.spotify_sp_dc
    if not sp_dc:
        return None

    cached = _SP_DC_TOKEN.get("access_token")
    if cached and time.time() < float(_SP_DC_TOKEN.get("expires_at") or 0):
        return cached  # type: ignore

    try:
        resp = requests.get(
            "https://open.spotify.com/get_access_token",
            params={"reason": "transport", "productType": "web_player"},
            headers={
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Cookie": f"sp_dc={sp_dc}",
                "Referer": "https://open.spotify.com/",
            },
            timeout=10,
        )
        if resp.status_code != 200:
            logger.warning(f"sp_dc token fetch failed ({resp.status_code}) — cookie may be expired")
            return None
        data = resp.json()
        token = data.get("accessToken")
        if not token:
            return None
        expires_ms = data.get("accessTokenExpirationTimestampMs", 0)
        _SP_DC_TOKEN["access_token"] = token
        _SP_DC_TOKEN["expires_at"] = expires_ms / 1000 - 30 if expires_ms else time.time() + 3600
        logger.info("Fetched Spotify web player token via sp_dc")
        return token
    except Exception as e:
        logger.warning(f"sp_dc token fetch error: {e}")
        return None


def _save_user_token() -> None:
    try:
        with open(_TOKEN_FILE, "w") as f:
            json.dump({
                "access_token": _USER_TOKEN["access_token"],
                "refresh_token": _USER_TOKEN["refresh_token"],
                "expires_at": _USER_TOKEN["expires_at"],
            }, f)
    except OSError as e:
        logger.warning(f"Could not save Spotify user token: {e}")


def _load_user_token() -> None:
    if not os.path.exists(_TOKEN_FILE):
        return
    try:
        with open(_TOKEN_FILE) as f:
            data = json.load(f)
        _USER_TOKEN["access_token"] = data.get("access_token")
        _USER_TOKEN["refresh_token"] = data.get("refresh_token")
        _USER_TOKEN["expires_at"] = float(data.get("expires_at") or 0)
        if _USER_TOKEN["refresh_token"]:
            logger.info("Loaded persisted Spotify user token from disk")
    except (OSError, json.JSONDecodeError, ValueError) as e:
        logger.warning(f"Could not load Spotify user token: {e}")


# Load on module import
_load_user_token()


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


def get_oauth_url() -> str:
    """Return the Spotify OAuth authorization URL for the user to visit."""
    cid, _ = _get_client_creds()
    settings = get_settings()
    params = {
        "client_id": cid,
        "response_type": "code",
        "redirect_uri": settings.spotify_redirect_uri,
        "scope": _OAUTH_SCOPES,
        "show_dialog": "false",
    }
    return f"{_AUTH_URL}?{urllib.parse.urlencode(params)}"


def handle_oauth_callback(code: str) -> None:
    """Exchange OAuth code for user tokens and store them."""
    cid, secret = _get_client_creds()
    settings = get_settings()
    auth_header = base64.b64encode(f"{cid}:{secret}".encode()).decode()
    resp = requests.post(
        _TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": settings.spotify_redirect_uri,
        },
        headers={"Authorization": f"Basic {auth_header}"},
        timeout=10,
    )
    if resp.status_code != 200:
        raise SpotifyAPIError(f"Spotify OAuth token exchange failed ({resp.status_code}): {resp.text}")
    data = resp.json()
    _USER_TOKEN["access_token"] = data["access_token"]
    _USER_TOKEN["refresh_token"] = data.get("refresh_token")
    _USER_TOKEN["expires_at"] = time.time() + data.get("expires_in", 3600) - 30
    _save_user_token()
    logger.info("Stored Spotify user OAuth token")


def _refresh_user_token() -> str:
    """Refresh the user access token using the stored refresh token."""
    cid, secret = _get_client_creds()
    auth_header = base64.b64encode(f"{cid}:{secret}".encode()).decode()
    resp = requests.post(
        _TOKEN_URL,
        data={"grant_type": "refresh_token", "refresh_token": _USER_TOKEN["refresh_token"]},
        headers={"Authorization": f"Basic {auth_header}"},
        timeout=10,
    )
    if resp.status_code != 200:
        # Refresh token expired — clear user token so we fall back to client creds
        _USER_TOKEN["access_token"] = None
        _USER_TOKEN["refresh_token"] = None
        _USER_TOKEN["expires_at"] = 0.0
        try:
            os.remove(_TOKEN_FILE)
        except OSError:
            pass
        raise SpotifyAPIError(f"Spotify token refresh failed ({resp.status_code}): {resp.text}")
    data = resp.json()
    _USER_TOKEN["access_token"] = data["access_token"]
    if data.get("refresh_token"):
        _USER_TOKEN["refresh_token"] = data["refresh_token"]
    _USER_TOKEN["expires_at"] = time.time() + data.get("expires_in", 3600) - 30
    _save_user_token()
    logger.info("Refreshed Spotify user OAuth token")
    return data["access_token"]


def get_auth_status() -> Dict:
    """Return current auth connection status."""
    has_user_token = bool(_USER_TOKEN.get("access_token"))
    user_expired = has_user_token and time.time() >= float(_USER_TOKEN.get("expires_at") or 0)
    settings = get_settings()
    return {
        "connected": has_user_token and not user_expired,
        "has_refresh_token": bool(_USER_TOKEN.get("refresh_token")),
        "sp_dc_configured": bool(settings.spotify_sp_dc),
    }


def _oembed_title(spotify_url: str) -> Optional[str]:
    """Fetch the playlist/album title from Spotify's public oEmbed endpoint (no auth needed)."""
    try:
        r = requests.get(
            "https://open.spotify.com/oembed",
            params={"url": spotify_url},
            timeout=8,
        )
        if r.status_code == 200:
            return r.json().get("title")
    except Exception:
        pass
    return None


def _ytmusic_tracks_for_query(query: str, max_items: int = 100) -> List[Dict]:
    """Search YouTube Music for a playlist matching query and return its tracks."""
    try:
        from ytmusicapi import YTMusic
        yt = YTMusic()

        # Try to find a matching playlist
        results = yt.search(query, filter="playlists", limit=5)
        for result in results:
            browse_id = result.get("browseId") or result.get("playlistId")
            title = result.get("title", "")
            if not browse_id:
                continue
            # Prefer results whose title closely matches the query
            try:
                playlist = yt.get_playlist(browse_id, limit=max_items)
            except Exception:
                continue
            tracks: List[Dict] = []
            for item in (playlist.get("tracks") or [])[:max_items]:
                name = item.get("title", "Unknown")
                artists = item.get("artists") or []
                artist_str = ", ".join(a.get("name", "") for a in artists if a) or "Unknown"
                album = (item.get("album") or {}).get("name")
                tracks.append({"title": name, "artist": artist_str, "album": album, "spotify_url": None})
            if tracks:
                logger.info(f"YouTube Music fallback: found '{title}' with {len(tracks)} tracks for query '{query}'")
                return tracks, title

    except Exception as e:
        logger.warning(f"YouTube Music fallback failed: {e}")
    return [], query


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
    """Return the best available token: sp_dc > user OAuth > client credentials."""
    # 1. Try sp_dc web player token (can access editorial playlists)
    sp_dc_token = _get_sp_dc_token()
    if sp_dc_token:
        return sp_dc_token

    # 2. Try user OAuth token — reload from disk if not in memory (multi-worker safe)
    if not _USER_TOKEN.get("access_token"):
        _load_user_token()
    user_token = _USER_TOKEN.get("access_token")
    if user_token:
        if time.time() < float(_USER_TOKEN.get("expires_at") or 0):
            return user_token  # type: ignore
        if _USER_TOKEN.get("refresh_token"):
            try:
                return _refresh_user_token()
            except SpotifyAPIError:
                logger.warning("User token refresh failed, falling back to client credentials")

    # 3. Fall back to client credentials
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
    if resp.status_code == 404:
        raise SpotifyAPIError("__editorial_404__")
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
        try:
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
        except SpotifyAPIError as e:
            if "__editorial_404__" not in str(e):
                raise
            # Editorial/restricted playlist — try YouTube Music fallback
            oembed_title = _oembed_title(url) or f"spotify_playlist_{resource_id[:8]}"
            logger.warning(
                f"Spotify API blocked playlist '{oembed_title}' (editorial restriction). "
                "Falling back to YouTube Music."
            )
            tracks, yt_title = _ytmusic_tracks_for_query(oembed_title)
            if not tracks:
                raise SpotifyAPIError(
                    f"Playlist '{oembed_title}' is an editorial/restricted Spotify playlist that cannot be accessed "
                    "via the API from a server. YouTube Music fallback also found no matching tracks. "
                    "To fix this permanently, apply for Extended Quota Mode on the Spotify Developer Dashboard."
                )
            return {
                "playlist_title": oembed_title,
                "description": f"YouTube Music fallback for Spotify editorial playlist '{oembed_title}'",
                "owner": "Spotify editorial (via YouTube Music)",
                "track_count": len(tracks),
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


_MIN_MP3_SIZE_BYTES = 50 * 1024  # 50 KB — anything smaller is not real audio


def _yt_audio_opts(download_dir: str, bitrate: str | None) -> Dict:
    return {
        "outtmpl": os.path.join(download_dir, "%(title)s.%(ext)s"),
        "quiet": True,
        "noplaylist": True,
        "format": "bestaudio[ext!=mhtml]/bestaudio/best",
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": bitrate or "192",
            }
        ],
    }


def _validate_mp3(filepath: str) -> None:
    """Raise if filepath is not a usable MP3 file."""
    if not os.path.exists(filepath):
        raise SpotifyAPIError(f"Expected MP3 not found: {filepath}")
    size = os.path.getsize(filepath)
    if size < _MIN_MP3_SIZE_BYTES:
        os.remove(filepath)
        raise SpotifyAPIError(f"Downloaded file is too small ({size} bytes) — not valid audio")
    # Check magic bytes: ID3 tag or raw MPEG sync word
    with open(filepath, "rb") as f:
        header = f.read(3)
    if header[:3] != b"ID3" and header[:2] not in (b"\xff\xfb", b"\xff\xfa", b"\xff\xf3", b"\xff\xf2", b"\xff\xe3", b"\xff\xe2"):
        os.remove(filepath)
        raise SpotifyAPIError(f"Downloaded file is not a valid MP3 (header: {header!r})")


def mirror_to_youtube(url: str, bitrate: str | None = "192", job_id: str | None = None) -> Dict:
    settings = get_settings()

    if job_id:
        _start_progress(job_id, job_type="spotify", message="Fetching Spotify playlist info", total=None)

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
        def _try_download(search_query: str):
            """Attempt a single yt-dlp search+download. Returns (entry, filepath, size_mb)."""
            import yt_dlp as _yt_dlp
            with _yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(f"ytsearch1:{search_query}", download=True)
                entry = None
                if info.get("entries"):
                    entry = info["entries"][0]
                if not entry:
                    raise SpotifyAPIError(f"No search result for {search_query}")
                fp = ydl.prepare_filename(entry)
                if not fp.endswith(".mp3"):
                    base, _ = os.path.splitext(fp)
                    fp = base + ".mp3"
                _validate_mp3(fp)
                sz = os.path.getsize(fp) / (1024 * 1024)
                return entry, fp, sz

        try:
            entry = None
            filepath = None
            size_mb = 0.0
            last_exc = None
            for attempt_query in (query, f"{title} {artist} official audio"):
                try:
                    entry, filepath, size_mb = _try_download(attempt_query)
                    break
                except Exception as exc:
                    last_exc = exc
                    logger.warning(f"Download attempt failed for '{attempt_query}': {exc}")
            if entry is None:
                raise last_exc or SpotifyAPIError(f"All download attempts failed for {query}")

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
            # Write ID3 tags using YouTube thumbnail + Spotify metadata
            upload_date = entry.get("upload_date", "")
            year = upload_date[:4] if upload_date and len(upload_date) >= 4 else None
            _write_id3_tags(
                filepath,
                title=entry.get("title", title),
                artist=artist,
                album=track.get("album"),
                year=year,
                artwork_url=entry.get("thumbnail"),
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
