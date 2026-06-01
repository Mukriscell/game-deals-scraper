import os
import threading

import psycopg2
import psycopg2.extras
import psycopg2.pool
import psycopg2.extensions

_pool: psycopg2.pool.ThreadedConnectionPool | None = None
_lock = threading.Lock()
_MAX_CONN = 8


def _build_pool() -> psycopg2.pool.ThreadedConnectionPool:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL no está definida en el entorno")
    return psycopg2.pool.ThreadedConnectionPool(2, _MAX_CONN, url)


class _PooledConn:
    """
    Proxy around a psycopg2 connection that returns it to the pool on close()
    instead of destroying it. All other attributes are forwarded transparently.
    """

    __slots__ = ("_conn",)

    def __init__(self, conn):
        object.__setattr__(self, "_conn", conn)

    def __getattr__(self, name):
        return getattr(object.__getattribute__(self, "_conn"), name)

    def close(self):
        conn = object.__getattribute__(self, "_conn")
        # Roll back any open transaction so the next caller gets a clean state
        try:
            if (not conn.closed and
                    conn.status == psycopg2.extensions.STATUS_IN_TRANSACTION):
                conn.rollback()
        except Exception:
            pass
        try:
            _pool.putconn(conn)
        except Exception:
            try:
                conn.close()
            except Exception:
                pass


def get_connection() -> _PooledConn:
    global _pool
    with _lock:
        if _pool is None or _pool.closed:
            _pool = _build_pool()

    try:
        conn = _pool.getconn()
        # Reconnect if the underlying socket died (e.g. Neon scale-to-zero)
        if conn.closed:
            try:
                _pool.putconn(conn)
            except Exception:
                pass
            conn = _pool.getconn()
        return _PooledConn(conn)
    except Exception:
        # Pool exhausted or broken — fall back to a direct connection
        url = os.environ.get("DATABASE_URL")
        return psycopg2.connect(url)  # type: ignore[return-value]
