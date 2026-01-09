import asyncio
import os
from datetime import datetime
from typing import Dict, Literal
import logging

import yt_dlp

from app.core.config import get_settings
from app.services import db_manager

DownloadKind = Literal["audio", "video"]


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _sanitize(name: str) -> str:
    clean = "".join(c for c in name if c.isalnum() or c in (" ", "-", "_"))
    clean = clean.strip().replace(" ", "_")
    return clean or "playlist"


def _base_opts(download_dir: str) -> Dict:
    return {
        "outtmpl": os.path.join(download_dir, "%(title)s.%(ext)s"),
        "quiet": True,
        "noplaylist": True,
        "merge_output_format": "mp4",
    }


def download_audio(url: str, bitrate: str | None = "192") -> Dict:
    logging.info(f"Starting audio download for URL: {url}")
    settings = get_settings()
    download_dir = os.path.join(settings.download_dir, "singledls")
    _ensure_dir(download_dir)
    opts = _base_opts(download_dir)
    opts.update(
        {
            "format": "bestaudio/best",
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": bitrate or "192",
                }
            ],
        }
    )
    with yt_dlp.YoutubeDL(opts) as ydl:
        logging.info(f"Extracting info and downloading audio from {url}")
        info = ydl.extract_info(url, download=True)
        filepath = ydl.prepare_filename(info)
        # FFmpegExtractAudio rewrites ext to .mp3
        if not filepath.endswith(".mp3"):
            base, _ = os.path.splitext(filepath)
            filepath = base + ".mp3"
    logging.info(f"Audio extraction and download finished for {url}")
    size_mb = round(os.path.getsize(filepath) / (1024 * 1024), 2)
    duration_minutes = round((info.get("duration") or 0) / 60, 2)
    downloaded_at = datetime.utcnow()
    db_manager.store_song(
        kind="audio",
        title=info.get("title", "unknown"),
        length_minutes=duration_minutes,
        size_mb=size_mb,
        downloaded_at=downloaded_at,
        url=url,
    )
    logging.info(f"Audio download completed: {filepath}")
    return {
        "title": info.get("title", "unknown"),
        "filepath": filepath,
        "size_mb": size_mb,
        "duration_minutes": duration_minutes,
        "downloaded_at": downloaded_at,
        "url": url,
        "kind": "audio",
    }


def download_video(url: str, resolution: str | None = None) -> Dict:
    logging.info(f"Starting video download for URL: {url}")
    settings = get_settings()
    download_dir = os.path.join(settings.download_dir, "singledls")
    _ensure_dir(download_dir)
    opts = _base_opts(download_dir)
    fmt = "bestvideo+bestaudio/best" if resolution in (None, "highest") else f"bestvideo[height<={resolution[:-1]}]+bestaudio/best"
    opts.update({"format": fmt})
    with yt_dlp.YoutubeDL(opts) as ydl:
        logging.info(f"Extracting info and downloading video from {url}")
        info = ydl.extract_info(url, download=True)
        filepath = ydl.prepare_filename(info)
    logging.info(f"Video extraction and download finished for {url}")
    size_mb = round(os.path.getsize(filepath) / (1024 * 1024), 2)
    duration_minutes = round((info.get("duration") or 0) / 60, 2)
    downloaded_at = datetime.utcnow()
    db_manager.store_song(
        kind="video",
        title=info.get("title", "unknown"),
        length_minutes=duration_minutes,
        size_mb=size_mb,
        downloaded_at=downloaded_at,
        url=url,
    )
    logging.info(f"Video download completed: {filepath}")
    return {
        "title": info.get("title", "unknown"),
        "filepath": filepath,
        "size_mb": size_mb,
        "duration_minutes": duration_minutes,
        "downloaded_at": downloaded_at,
        "url": url,
        "kind": "video",
    }


async def download(kind: DownloadKind, url: str, resolution: str | None = None, bitrate: str | None = None) -> Dict:
    if kind == "audio":
        return await asyncio.to_thread(download_audio, url, bitrate)
    return await asyncio.to_thread(download_video, url, resolution)


def _playlist_opts(download_dir: str, for_video: bool, resolution: str | None, bitrate: str | None) -> Dict:
    opts = _base_opts(download_dir)
    opts["noplaylist"] = False
    if for_video:
        fmt = "bestvideo+bestaudio/best" if resolution in (None, "highest") else f"bestvideo[height<={resolution[:-1]}]+bestaudio/best"
        opts.update({"format": fmt})
    else:
        opts.update(
            {
                "format": "bestaudio/best",
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": bitrate or "192",
                    }
                ],
            }
        )
    return opts


def download_playlist(kind: DownloadKind, url: str, resolution: str | None = None, bitrate: str | None = None) -> Dict:
    logging.info(f"Starting playlist download for URL: {url}")
    settings = get_settings()
    base_dir = os.path.join(settings.download_dir, "playlists")
    _ensure_dir(base_dir)

    # First fetch metadata to get playlist title without downloading.
    meta_opts = _playlist_opts(base_dir, for_video=(kind == "video"), resolution=resolution, bitrate=bitrate)
    with yt_dlp.YoutubeDL(meta_opts) as ydl_meta:
        logging.info(f"Extracting playlist metadata from {url}")
        info = ydl_meta.extract_info(url, download=False)
    logging.info(f"Playlist metadata extracted: {info.get('title', 'unknown')}")

    playlist_title = info.get("title") or "playlist"
    playlist_dir = os.path.join(base_dir, _sanitize(playlist_title))
    _ensure_dir(playlist_dir)

    # Rebuild opts to download directly into the playlist folder.
    opts = _playlist_opts(playlist_dir, for_video=(kind == "video"), resolution=resolution, bitrate=bitrate)
    opts["outtmpl"] = os.path.join(playlist_dir, "%(title)s.%(ext)s")

    items = []
    with yt_dlp.YoutubeDL(opts) as ydl:
        logging.info(f"Downloading playlist items from {url} to {playlist_dir}")
        info = ydl.extract_info(url, download=True)
        logging.info(f"Playlist download extraction finished for {url}")
        entries = info.get("entries", []) or []
        for entry in entries:
            if not entry:
                continue
            title = entry.get("title", "unknown")
            duration_minutes = round((entry.get("duration") or 0) / 60, 2)
            base_fn = ydl.prepare_filename(entry)
            filepath = base_fn
            if kind == "audio" and not filepath.endswith(".mp3"):
                base, _ = os.path.splitext(base_fn)
                filepath = base + ".mp3"
            if not os.path.exists(filepath):
                alt = base_fn.rsplit(".", 1)[0]
                for ext in (".mp3", ".mp4", ".m4a"):
                    candidate = alt + ext
                    if os.path.exists(candidate):
                        filepath = candidate
                        break
            size_mb = round(os.path.getsize(filepath) / (1024 * 1024), 2) if os.path.exists(filepath) else 0
            downloaded_at = datetime.utcnow()
            db_manager.store_song(
                kind=kind,
                title=title,
                length_minutes=duration_minutes,
                size_mb=size_mb,
                downloaded_at=downloaded_at,
                url=entry.get("webpage_url", url),
            )
            items.append(
                {
                    "title": title,
                    "filepath": filepath,
                    "size_mb": size_mb,
                    "duration_minutes": duration_minutes,
                    "downloaded_at": downloaded_at,
                    "url": entry.get("webpage_url", url),
                    "kind": kind,
                }
            )
    logging.info(f"Playlist download completed: {len(items)} items in {playlist_title}")
    return {"count": len(items), "items": items, "playlist_title": playlist_title}


async def download_playlist_async(kind: DownloadKind, url: str, resolution: str | None = None, bitrate: str | None = None) -> Dict:
    return await asyncio.to_thread(download_playlist, kind, url, resolution, bitrate)
