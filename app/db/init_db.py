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
