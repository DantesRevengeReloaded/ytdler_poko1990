import asyncio
import os
from datetime import datetime
from typing import Dict, Literal
import logging
import uuid
from threading import Lock

import yt_dlp

from app.core.config import get_settings
from app.services import db_manager

DownloadKind = Literal["audio", "video"]


# Simple in-memory progress store. Good enough for single-user/session use.
_progress: Dict[str, Dict] = {}
_progress_lock = Lock()


def _set_progress(job_id: str, **fields) -> None:
    with _progress_lock:
        current = _progress.get(job_id, {})
        current.update(fields)
        _progress[job_id] = current


def _start_progress(job_id: str, job_type: str, message: str = "", total: int | None = None) -> None:
    now = datetime.utcnow()
    _set_progress(
        job_id,
        job_type=job_type,
        phase="start",
        message=message,
        total=total,
        completed=0,
        started_at=now,
        updated_at=now,
        error=None,
    )


def _finish_progress(job_id: str, message: str = "Completed", error: str | None = None) -> None:
    now = datetime.utcnow()
    entry = _progress.get(job_id, {})
    total = entry.get("total")
    completed = entry.get("completed") or 0
    _set_progress(
        job_id,
        phase="error" if error else "done",
        message=message if not error else error,
        error=error,
        completed=completed if completed is not None else total,
        updated_at=now,
    )


def get_progress(job_id: str) -> Dict | None:
    with _progress_lock:
        entry = _progress.get(job_id)
        return dict(entry) if entry else None


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


def download_audio(url: str, bitrate: str | None = "192", job_id: str | None = None) -> Dict:
    logging.info(f"Starting audio download for URL: {url}")
    started_at = datetime.utcnow()
    settings = get_settings()
    download_dir = os.path.join(settings.download_dir, "singledls")
    _ensure_dir(download_dir)
    if job_id:
        _start_progress(job_id, job_type="single", message="Fetching metadata", total=1)
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
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            logging.info(f"Extracting info and downloading audio from {url}")
            info = ydl.extract_info(url, download=True)
            if job_id:
                _set_progress(job_id, phase="downloading", message="Downloading audio", completed=0, updated_at=datetime.utcnow())
            filepath = ydl.prepare_filename(info)
            # FFmpegExtractAudio rewrites ext to .mp3
            if not filepath.endswith(".mp3"):
                base, _ = os.path.splitext(filepath)
                filepath = base + ".mp3"
    except Exception as exc:
        if job_id:
            _finish_progress(job_id, error=str(exc), message="Failed")
        raise
    logging.info(f"Audio extraction and download finished for {url}")
    size_mb = round(os.path.getsize(filepath) / (1024 * 1024), 2)
    duration_minutes = round((info.get("duration") or 0) / 60, 2)
    downloaded_at = datetime.utcnow()
    duration_seconds = (downloaded_at - started_at).total_seconds()
    if job_id:
        _set_progress(job_id, phase="finishing", message="Finalizing", completed=1, total=1, updated_at=downloaded_at)
    db_manager.store_song(
        kind="audio",
        title=info.get("title", "unknown"),
        length_minutes=duration_minutes,
        size_mb=size_mb,
        downloaded_at=downloaded_at,
        url=url,
    )
    logging.info(f"Audio download completed: {filepath}")
    if job_id:
        _finish_progress(job_id, message="Completed")
    return {
        "title": info.get("title", "unknown"),
        "filepath": filepath,
        "size_mb": size_mb,
        "duration_minutes": duration_minutes,
        "downloaded_at": downloaded_at,
        "url": url,
        "kind": "audio",
        "job_id": job_id or "",
        "duration_seconds": duration_seconds,
    }


def download_video(url: str, resolution: str | None = None, job_id: str | None = None) -> Dict:
    logging.info(f"Starting video download for URL: {url}")
    started_at = datetime.utcnow()
    settings = get_settings()
    download_dir = os.path.join(settings.download_dir, "singledls")
    _ensure_dir(download_dir)
    if job_id:
        _start_progress(job_id, job_type="single", message="Fetching metadata", total=1)
    opts = _base_opts(download_dir)
    fmt = "bestvideo+bestaudio/best" if resolution in (None, "highest") else f"bestvideo[height<={resolution[:-1]}]+bestaudio/best"
    opts.update({"format": fmt})
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            logging.info(f"Extracting info and downloading video from {url}")
            info = ydl.extract_info(url, download=True)
            if job_id:
                _set_progress(job_id, phase="downloading", message="Downloading video", completed=0, updated_at=datetime.utcnow())
            filepath = ydl.prepare_filename(info)
    except Exception as exc:
        if job_id:
            _finish_progress(job_id, error=str(exc), message="Failed")
        raise
    logging.info(f"Video extraction and download finished for {url}")
    size_mb = round(os.path.getsize(filepath) / (1024 * 1024), 2)
    duration_minutes = round((info.get("duration") or 0) / 60, 2)
    downloaded_at = datetime.utcnow()
    duration_seconds = (downloaded_at - started_at).total_seconds()
    if job_id:
        _set_progress(job_id, phase="finishing", message="Finalizing", completed=1, total=1, updated_at=downloaded_at)
    db_manager.store_song(
        kind="video",
        title=info.get("title", "unknown"),
        length_minutes=duration_minutes,
        size_mb=size_mb,
        downloaded_at=downloaded_at,
        url=url,
    )
    logging.info(f"Video download completed: {filepath}")
    if job_id:
        _finish_progress(job_id, message="Completed")
    return {
        "title": info.get("title", "unknown"),
        "filepath": filepath,
        "size_mb": size_mb,
        "duration_minutes": duration_minutes,
        "downloaded_at": downloaded_at,
        "url": url,
        "kind": "video",
        "job_id": job_id or "",
        "duration_seconds": duration_seconds,
    }


async def download(kind: DownloadKind, url: str, resolution: str | None = None, bitrate: str | None = None, job_id: str | None = None) -> Dict:
    if kind == "audio":
        return await asyncio.to_thread(download_audio, url, bitrate, job_id)
    return await asyncio.to_thread(download_video, url, resolution, job_id)


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


def download_playlist(kind: DownloadKind, url: str, resolution: str | None = None, bitrate: str | None = None, job_id: str | None = None) -> Dict:
    logging.info(f"Starting playlist download for URL: {url}")
    started_at = datetime.utcnow()
    settings = get_settings()
    base_dir = os.path.join(settings.download_dir, "playlists")
    _ensure_dir(base_dir)

    if job_id:
        _start_progress(job_id, job_type="playlist", message="Fetching playlist metadata", total=None)

    # First fetch metadata to get playlist title without downloading.
    meta_opts = _playlist_opts(base_dir, for_video=(kind == "video"), resolution=resolution, bitrate=bitrate)
    try:
        with yt_dlp.YoutubeDL(meta_opts) as ydl_meta:
            logging.info(f"Extracting playlist metadata from {url}")
            info = ydl_meta.extract_info(url, download=False)
        logging.info(f"Playlist metadata extracted: {info.get('title', 'unknown')}")
    except Exception as exc:
        if job_id:
            _finish_progress(job_id, error=str(exc), message="Metadata failed")
        raise

    entries_meta = info.get("entries", []) or []
    # Filter out None entries defensively
    entries_meta = [e for e in entries_meta if e]
    total_entries = len(entries_meta)
    if job_id:
        _set_progress(
            job_id,
            phase="metadata",
            message=f"Found {total_entries} songs in playlist",
            total=total_entries or None,
            updated_at=datetime.utcnow(),
        )

    playlist_title = info.get("title") or "playlist"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    playlist_dir_name = f"{_sanitize(playlist_title)}_{timestamp}"
    playlist_dir = os.path.join(base_dir, playlist_dir_name)
    _ensure_dir(playlist_dir)
    if job_id:
        _set_progress(
            job_id,
            playlist_title=playlist_title,
            message=f"{playlist_title}: Total {total_entries} songs",
            phase="queued",
            total=total_entries or None,
            updated_at=datetime.utcnow(),
        )

    # Rebuild opts to download directly into the playlist folder.
    opts = _playlist_opts(playlist_dir, for_video=(kind == "video"), resolution=resolution, bitrate=bitrate)
    opts["outtmpl"] = os.path.join(playlist_dir, "%(playlist_index)03d_%(title)s.%(ext)s")

    items = []
    try:
        entries = entries_meta
        total_for_progress = total_entries or len(entries)
        if job_id:
            _set_progress(
                job_id,
                total=total_for_progress or None,
                message=f"{playlist_title}: Total {total_for_progress or 'unknown'} songs",
                updated_at=datetime.utcnow(),
            )

        for idx, entry in enumerate(entries, start=1):
            if not entry:
                continue
            entry_url = entry.get("webpage_url") or entry.get("url") or entry.get("id") or url
            entry_opts = dict(opts)
            entry_opts["outtmpl"] = os.path.join(playlist_dir, f"{idx:03d}_%(title)s.%(ext)s")
            with yt_dlp.YoutubeDL(entry_opts) as ydl:
                info = ydl.extract_info(entry_url, download=True)
                title = info.get("title", entry.get("title", "unknown"))
                duration_minutes = round((info.get("duration") or 0) / 60, 2)
                base_fn = ydl.prepare_filename(info)
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
                if job_id:
                    _set_progress(
                        job_id,
                        phase="downloading",
                        message=f"{playlist_title}: Total {total_for_progress} songs {idx}/{total_for_progress} downloaded",
                        completed=idx,
                        total=total_for_progress or None,
                        updated_at=downloaded_at,
                        playlist_title=playlist_title,
                    )
                db_manager.store_song(
                    kind=kind,
                    title=title,
                    length_minutes=duration_minutes,
                    size_mb=size_mb,
                    downloaded_at=downloaded_at,
                    url=entry_url,
                )
                items.append(
                    {
                        "title": title,
                        "filepath": filepath,
                        "size_mb": size_mb,
                        "duration_minutes": duration_minutes,
                        "downloaded_at": downloaded_at,
                        "url": entry_url,
                        "kind": kind,
                        "job_id": job_id or "",
                    }
                )
    except Exception as exc:
        if job_id:
            _finish_progress(job_id, error=str(exc), message="Failed")
        raise
    logging.info(f"Playlist download completed: {len(items)} items in {playlist_title}")
    finished_at = datetime.utcnow()
    duration_seconds = (finished_at - started_at).total_seconds()
    if job_id:
        total_for_progress = total_entries or len(items)
        _finish_progress(job_id, message=f"{playlist_title}: Downloaded {len(items)}/{total_for_progress} songs")
    return {"count": len(items), "items": items, "playlist_title": playlist_title, "job_id": job_id or "", "duration_seconds": duration_seconds}


async def download_playlist_async(kind: DownloadKind, url: str, resolution: str | None = None, bitrate: str | None = None, job_id: str | None = None) -> Dict:
    return await asyncio.to_thread(download_playlist, kind, url, resolution, bitrate, job_id)
