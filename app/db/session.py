import psycopg2
from contextlib import contextmanager

from app.core.config import db_dsn

_dsn = None


def init_pool() -> None:
    global _dsn
    _dsn = db_dsn()


def get_conn():
    if _dsn is None:
        init_pool()
    return psycopg2.connect(_dsn)


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
