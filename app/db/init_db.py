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
        cur.execute("CREATE INDEX IF NOT EXISTS idx_ds_url ON downloaded_songs (url);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_ds_date ON downloaded_songs (downloaded_date);")

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS spotify_downloads (
                id SERIAL PRIMARY KEY,
                playlist_title TEXT,
                source_type TEXT,
                track_title TEXT,
                artist TEXT,
                query TEXT,
                filepath TEXT,
                status TEXT,
                error TEXT,
                downloaded_date TIMESTAMPTZ
            );
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY,
                job_type TEXT,
                phase TEXT,
                message TEXT,
                total INTEGER,
                completed INTEGER,
                playlist_title TEXT,
                error TEXT,
                started_at TIMESTAMPTZ,
                updated_at TIMESTAMPTZ
            );
            """
        )
