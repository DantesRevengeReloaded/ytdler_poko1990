import sqlite3
import os
from contextlib import contextmanager

from app.core.config import get_settings

_db_path = None


def init_pool() -> None:
    global _db_path
    settings = get_settings()
    _db_path = os.path.join(settings.download_dir, 'downloads.db')


def get_conn():
    if _db_path is None:
        init_pool()
    return sqlite3.connect(_db_path)


@contextmanager
def get_cursor():
    conn = get_conn()
    cur = conn.cursor()
    try:
        yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()
