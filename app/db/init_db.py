from app.db.session import get_cursor


def ensure_tables() -> None:
    with get_cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS downloaded_songs (
                id SERIAL PRIMARY KEY,
                type TEXT NOT NULL,
                title TEXT NOT NULL,
                time_length DOUBLE PRECISION,
                size_mb DOUBLE PRECISION,
                downloaded_date TIMESTAMPTZ,
                url TEXT
            );
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS spotify_downloads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                playlist_title TEXT,
                source_type TEXT,
                track_title TEXT,
                artist TEXT,
                query TEXT,
                filepath TEXT,
                status TEXT,
                error TEXT,
                downloaded_date TEXT
            );
            """
        )
