from datetime import datetime
from typing import Optional

from app.db.init_db import ensure_tables
from app.db.session import get_cursor


def init_db() -> None:
    ensure_tables()


def store_song(kind: str, title: str, length_minutes: float, size_mb: float, downloaded_at: datetime, url: str) -> None:
    ensure_tables()
    with get_cursor() as cur:
        cur.execute(
            """
            INSERT INTO downloaded_songs (type, title, time_length, size_mb, downloaded_date, url)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (kind, title, length_minutes, size_mb, downloaded_at.isoformat(), url),
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
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                downloaded_at.isoformat(),
            ),
        )
