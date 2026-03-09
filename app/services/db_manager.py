import logging
import os
from datetime import datetime
from typing import Optional

from app.db.init_db import ensure_tables
from app.db.session import get_cursor

logger = logging.getLogger(__name__)


def init_db() -> None:
    ensure_tables()


def store_song(kind: str, title: str, length_minutes: float, size_mb: float, downloaded_at: datetime, url: str) -> None:
    ensure_tables()
    with get_cursor() as cur:
        cur.execute(
            """
            INSERT INTO downloaded_songs (type, title, time_length, size_mb, downloaded_date, url)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (kind, title, length_minutes, size_mb, downloaded_at, url),
        )


def get_total_size() -> float:
    ensure_tables()
    with get_cursor() as cur:
        cur.execute("SELECT COALESCE(SUM(size_mb), 0) FROM downloaded_songs")
        result = cur.fetchone()[0]
        return float(result or 0)


def get_total_songs() -> float:
    ensure_tables()
    with get_cursor() as cur:
        cur.execute("SELECT COALESCE(COUNT(*), 0) FROM downloaded_songs")
        result = cur.fetchone()[0]
        return float(result or 0)


def get_history(limit: int = 50, offset: int = 0) -> list[dict]:
    ensure_tables()
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT id, type, title, time_length, size_mb, downloaded_date, url
            FROM downloaded_songs
            ORDER BY downloaded_date DESC
            LIMIT %s OFFSET %s
            """,
            (limit, offset),
        )
        rows = cur.fetchall()
        return [
            {
                "id": r[0],
                "type": r[1],
                "title": r[2],
                "time_length": r[3],
                "size_mb": r[4],
                "downloaded_date": r[5],
                "url": r[6],
            }
            for r in rows
        ]


def get_history_count() -> int:
    ensure_tables()
    with get_cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM downloaded_songs")
        return cur.fetchone()[0]


def get_spotify_history(limit: int = 50, offset: int = 0) -> list[dict]:
    ensure_tables()
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT id, playlist_title, source_type, track_title, artist, query, filepath, status, error, downloaded_date
            FROM spotify_downloads
            ORDER BY downloaded_date DESC
            LIMIT %s OFFSET %s
            """,
            (limit, offset),
        )
        rows = cur.fetchall()
        return [
            {
                "id": r[0],
                "playlist_title": r[1],
                "source_type": r[2],
                "track_title": r[3],
                "artist": r[4],
                "query": r[5],
                "filepath": r[6],
                "status": r[7],
                "error": r[8],
                "downloaded_date": r[9],
            }
            for r in rows
        ]


def get_spotify_history_count() -> int:
    ensure_tables()
    with get_cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM spotify_downloads")
        return cur.fetchone()[0]


def store_spotify_mirror_entry(
    playlist_title: str,
    source_type: str,
    track_title: str,
    artist: str,
    query: str,
    filepath: str | None,
    status: str,
    error: str | None,
    downloaded_at: datetime,
) -> None:
    ensure_tables()
    with get_cursor() as cur:
        cur.execute(
            """
            INSERT INTO spotify_downloads (
                playlist_title, source_type, track_title, artist, query,
                filepath, status, error, downloaded_date
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                playlist_title,
                source_type,
                track_title,
                artist,
                query,
                filepath,
                status,
                error,
                downloaded_at,
            ),
        )


def upsert_job(job_id: str, **fields) -> None:
    ensure_tables()
    with get_cursor() as cur:
        cur.execute(
            """
            INSERT INTO jobs (job_id, job_type, phase, message, total, completed, playlist_title, error, started_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (job_id) DO UPDATE SET
                phase = COALESCE(EXCLUDED.phase, jobs.phase),
                message = COALESCE(EXCLUDED.message, jobs.message),
                total = COALESCE(EXCLUDED.total, jobs.total),
                completed = COALESCE(EXCLUDED.completed, jobs.completed),
                playlist_title = COALESCE(EXCLUDED.playlist_title, jobs.playlist_title),
                error = EXCLUDED.error,
                updated_at = EXCLUDED.updated_at
            """,
            (
                job_id,
                fields.get("job_type"),
                fields.get("phase"),
                fields.get("message"),
                fields.get("total"),
                fields.get("completed"),
                fields.get("playlist_title"),
                fields.get("error"),
                fields.get("started_at"),
                fields.get("updated_at"),
            ),
        )


def get_job(job_id: str) -> dict | None:
    ensure_tables()
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT job_id, job_type, phase, message, total, completed, playlist_title, error, started_at, updated_at
            FROM jobs WHERE job_id = %s
            """,
            (job_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        return {
            "job_id": row[0],
            "job_type": row[1],
            "phase": row[2],
            "message": row[3],
            "total": row[4],
            "completed": row[5],
            "playlist_title": row[6],
            "error": row[7],
            "started_at": row[8],
            "updated_at": row[9],
        }


def get_recent_jobs(limit: int = 20) -> list[dict]:
    ensure_tables()
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT job_id, job_type, phase, message, total, completed, playlist_title, error, started_at, updated_at
            FROM jobs ORDER BY updated_at DESC LIMIT %s
            """,
            (limit,),
        )
        rows = cur.fetchall()
        return [
            {
                "job_id": r[0], "job_type": r[1], "phase": r[2], "message": r[3],
                "total": r[4], "completed": r[5], "playlist_title": r[6],
                "error": r[7], "started_at": r[8], "updated_at": r[9],
            }
            for r in rows
        ]


def get_stats_breakdown() -> list[dict]:
    ensure_tables()
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT type, COUNT(*) as count, COALESCE(SUM(size_mb), 0) as total_mb
            FROM downloaded_songs
            GROUP BY type
            ORDER BY count DESC
            """
        )
        rows = cur.fetchall()
        return [{"type": r[0], "count": int(r[1]), "total_mb": float(r[2])} for r in rows]


def get_storage_stats(download_dir: str) -> list[dict]:
    dirs = ["singledls", "playlists", "spotify_playlists"]
    result = []
    for d in dirs:
        path = os.path.join(download_dir, d)
        total_bytes = 0
        count = 0
        if os.path.exists(path):
            for dirpath, _dirnames, filenames in os.walk(path):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    try:
                        total_bytes += os.path.getsize(fp)
                        count += 1
                    except OSError:
                        pass
        result.append({"directory": d, "size_mb": round(total_bytes / (1024 * 1024), 2), "file_count": count})
    return result
