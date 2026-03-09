import os
import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.core.config import get_settings

router = APIRouter(prefix="/api/v1/files", tags=["files"])

_AUDIO_EXTENSIONS = {".mp3", ".m4a", ".ogg", ".flac", ".wav"}
_VIDEO_EXTENSIONS = {".mp4", ".mkv", ".webm", ".avi"}
_SKIP_EXTENSIONS = {".txt", ".json", ".part", ".ytdl"}


def _resolve_safe(filepath: str) -> str:
    """Resolve filepath relative to download_dir, rejecting any path traversal."""
    settings = get_settings()
    download_dir = os.path.abspath(settings.download_dir)
    candidate = os.path.abspath(os.path.join(download_dir, filepath))
    if not (candidate.startswith(download_dir + os.sep) or candidate == download_dir):
        raise HTTPException(status_code=400, detail="Invalid file path")
    return candidate


@router.get("")
async def list_files():
    settings = get_settings()
    download_dir = os.path.abspath(settings.download_dir)
    files = []
    for subdir in ("singledls", "playlists", "spotify_playlists"):
        dirpath = os.path.join(download_dir, subdir)
        if not os.path.exists(dirpath):
            continue
        for root, _dirs, filenames in os.walk(dirpath):
            for fname in filenames:
                ext = os.path.splitext(fname)[1].lower()
                if ext in _SKIP_EXTENSIONS or fname.startswith("."):
                    continue
                fp = os.path.join(root, fname)
                rel = os.path.relpath(fp, download_dir)
                try:
                    stat = os.stat(fp)
                    if ext in _AUDIO_EXTENSIONS:
                        ftype = "audio"
                    elif ext in _VIDEO_EXTENSIONS:
                        ftype = "video"
                    else:
                        continue
                    files.append({
                        "name": fname,
                        "path": rel,
                        "size_mb": round(stat.st_size / (1024 * 1024), 2),
                        "modified": stat.st_mtime,
                        "type": ftype,
                        "category": subdir,
                    })
                except OSError:
                    pass
    files.sort(key=lambda x: x["modified"], reverse=True)
    return {"files": files, "count": len(files)}


@router.get("/root")
async def get_output_root():
    settings = get_settings()
    download_dir = os.path.abspath(settings.download_dir)
    return {
        "root": download_dir,
        "folders": {
            "single": "singledls",
            "playlists": "playlists",
            "spotify": "spotify_playlists",
        },
    }


@router.get("/stream/{filepath:path}")
async def stream_file(filepath: str):
    full_path = _resolve_safe(filepath)
    if not os.path.isfile(full_path):
        raise HTTPException(status_code=404, detail="File not found")
    ext = os.path.splitext(full_path)[1].lower()
    if ext in _AUDIO_EXTENSIONS:
        media_type = "audio/mpeg" if ext == ".mp3" else "audio/mp4"
    elif ext in _VIDEO_EXTENSIONS:
        media_type = "video/mp4"
    else:
        media_type = "application/octet-stream"
    return FileResponse(full_path, media_type=media_type)


@router.delete("/{filepath:path}")
async def delete_file(filepath: str):
    full_path = _resolve_safe(filepath)
    if not os.path.isfile(full_path):
        raise HTTPException(status_code=404, detail="File not found")
    os.remove(full_path)
    logging.info(f"Deleted file: {full_path}")
    return {"deleted": filepath}
