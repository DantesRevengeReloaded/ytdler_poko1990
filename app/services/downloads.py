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

# Simple in-memory progress store. DB is used as fallback after restart.
_progress: Dict[str, Dict] = {}
_progress_lock = Lock()

# Semaphore initialized lazily on first async call.
_download_semaphore: asyncio.Semaphore | None = None


def _get_semaphore() -> asyncio.Semaphore:
    global _download_semaphore
    if _download_semaphore is None:
        settings = get_settings()
        _download_semaphore = asyncio.Semaphore(settings.max_concurrent_downloads)
    return _download_semaphore


def _set_progress(job_id: str, **fields) -> None:
    with _progress_lock:
        current = _progress.get(job_id, {})
        current.update(fields)
        _progress[job_id] = current
    try:
        db_manager.upsert_job(job_id, **fields)
    except Exception:
        pass


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
        if entry:
            return dict(entry)
    # Fallback to DB (survives restart)
    try:
        return db_manager.get_job(job_id)
    except Exception:
        return None


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


def _write_id3_tags(
    filepath: str,
    title: str,
    artist: str = "",
    album: str | None = None,
    year: str | None = None,
    artwork_url: str | None = None,
) -> None:
    try:
        from mutagen.id3 import ID3, TIT2, TPE1, TALB, TDRC, APIC
        from mutagen.mp3 import MP3
        import requests as req

        audio = MP3(filepath, ID3=ID3)
        try:
            audio.add_tags()
        except Exception:
            pass  # Tags already exist

        audio.tags["TIT2"] = TIT2(encoding=3, text=title)
        if artist:
            audio.tags["TPE1"] = TPE1(encoding=3, text=artist)
        if album:
            audio.tags["TALB"] = TALB(encoding=3, text=album)
        if year:
            audio.tags["TDRC"] = TDRC(encoding=3, text=str(year))
        if artwork_url:
            try:
                resp = req.get(artwork_url, timeout=10)
                if resp.status_code == 200:
                    audio.tags["APIC"] = APIC(
                        encoding=3,
                        mime="image/jpeg",
                        type=3,
                        desc="Cover",
                        data=resp.content,
                    )
            except Exception:
                pass
        audio.save(v2_version=3)
    except Exception as e:
        logging.warning(f"Could not write ID3 tags to {filepath}: {e}")


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
    # Write ID3 tags
    upload_date = info.get("upload_date", "")
    year = upload_date[:4] if upload_date and len(upload_date) >= 4 else None
    _write_id3_tags(
        filepath,
        title=info.get("title", "unknown"),
        artist=info.get("uploader") or info.get("channel") or "",
        year=year,
        artwork_url=info.get("thumbnail"),
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
    async with _get_semaphore():
        if kind == "audio":
            return await asyncio.to_thread(download_audio, url, bitrate, job_id)
        return await asyncio.to_thread(download_video, url, resolution, job_id)


def _playlist_opts(download_dir: str, for_video: bool, resolution: str | None, bitrate: str | None) -> Dict:
    opts = _base_opts(download_dir)
    opts["noplaylist"] = False
    opts["ignoreerrors"] = True
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

    opts = _playlist_opts(playlist_dir, for_video=(kind == "video"), resolution=resolution, bitrate=bitrate)
    opts["outtmpl"] = os.path.join(playlist_dir, "%(playlist_index)03d_%(title)s.%(ext)s")

    items = []
    failures: list[Dict[str, str | None]] = []
    try:
        entries = entries_meta
        total_for_progress = total_entries or len(entries)
        downloaded = 0
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
            entry_title = entry.get("title") or f"item_{idx}"
            entry_opts = dict(opts)
            entry_opts["outtmpl"] = os.path.join(playlist_dir, f"{idx:03d}_%(title)s.%(ext)s")
            entry_opts["ignoreerrors"] = True
            try:
                with yt_dlp.YoutubeDL(entry_opts) as ydl:
                    info = ydl.extract_info(entry_url, download=True)
                    title = info.get("title", entry_title)
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
                    downloaded += 1
                    if job_id:
                        _set_progress(
                            job_id,
                            phase="downloading",
                            message=f"{playlist_title}: Downloaded {downloaded}/{total_for_progress} songs",
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
                    if kind == "audio" and os.path.exists(filepath):
                        upload_date = info.get("upload_date", "")
                        year = upload_date[:4] if upload_date and len(upload_date) >= 4 else None
                        _write_id3_tags(
                            filepath,
                            title=title,
                            artist=info.get("uploader") or info.get("channel") or "",
                            year=year,
                            artwork_url=info.get("thumbnail"),
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
                error_msg = str(exc)
                logging.warning(f"Skipping playlist item {idx} ({entry_title}): {error_msg}")
                failures.append({"title": entry_title, "url": entry_url, "error": error_msg})
                if job_id:
                    _set_progress(
                        job_id,
                        phase="downloading",
                        message=f"{playlist_title}: Downloaded {downloaded}/{total_for_progress} songs (skipped {len(failures)})",
                        completed=idx,
                        total=total_for_progress or None,
                        updated_at=datetime.utcnow(),
                        playlist_title=playlist_title,
                    )
                continue
    except Exception as exc:
        if job_id:
            _finish_progress(job_id, error=str(exc), message="Failed")
        raise
    summary_total = total_entries or total_for_progress or (len(items) + len(failures))
    logging.info(f"Playlist download completed: {len(items)} items in {playlist_title} (skipped {len(failures)})")
    finished_at = datetime.utcnow()
    duration_seconds = (finished_at - started_at).total_seconds()
    if job_id:
        if len(items) == 0 and failures:
            _finish_progress(job_id, error=f"{playlist_title}: all {summary_total} songs failed")
        else:
            summary_message = f"{playlist_title}: Downloaded {len(items)}/{summary_total} songs"
            if failures:
                summary_message += f" (skipped {len(failures)})"
            _finish_progress(job_id, message=summary_message)
    return {
        "count": len(items),
        "items": items,
        "playlist_title": playlist_title,
        "job_id": job_id or "",
        "duration_seconds": duration_seconds,
        "failed": len(failures),
        "errors": failures,
    }


async def download_playlist_async(kind: DownloadKind, url: str, resolution: str | None = None, bitrate: str | None = None, job_id: str | None = None) -> Dict:
    async with _get_semaphore():
        return await asyncio.to_thread(download_playlist, kind, url, resolution, bitrate, job_id)


def cleanup_old_files() -> None:
    settings = get_settings()
    if not settings.cleanup_days:
        return
    import time
    cutoff = time.time() - (settings.cleanup_days * 86400)
    for subdir in ("singledls", "playlists", "spotify_playlists"):
        dirpath = os.path.join(settings.download_dir, subdir)
        if not os.path.exists(dirpath):
            continue
        for root, _dirs, files in os.walk(dirpath):
            for fname in files:
                fp = os.path.join(root, fname)
                try:
                    if os.path.getmtime(fp) < cutoff:
                        os.remove(fp)
                        logging.info(f"Cleanup: removed {fp}")
                except OSError:
                    pass
