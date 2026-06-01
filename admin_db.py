"""
admin_db.py — All admin-specific database tables and helpers.
"""
import json
import time

import psycopg2
import psycopg2.extras

from db import get_connection


def _con():
    return get_connection()


# ── Config in-memory cache (avoids a DB round-trip on every request) ──────────
_cfg_cache: dict = {}
_cfg_cache_ts: float = 0.0
_CFG_TTL = 30  # seconds


def _load_config_cache():
    global _cfg_cache, _cfg_cache_ts
    con = _con()
    cur = con.cursor()
    cur.execute("SELECT key, value FROM admin_config")
    _cfg_cache = {r[0]: r[1] for r in cur.fetchall()}
    _cfg_cache_ts = time.time()
    con.close()


# ══ Init ══════════════════════════════════════════════════════════════════════

def init_admin_tables():
    con = _con()
    cur = con.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS admin_config (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL DEFAULT ''
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS admin_log (
            id     SERIAL PRIMARY KEY,
            action TEXT NOT NULL,
            detail TEXT NOT NULL DEFAULT '',
            ts     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS login_attempts (
            id      SERIAL PRIMARY KEY,
            target  TEXT NOT NULL,
            ip      TEXT NOT NULL DEFAULT '',
            success INTEGER DEFAULT 0,
            ts      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS cache_history (
            id          SERIAL PRIMARY KEY,
            deals_count INTEGER DEFAULT 0,
            duration_ms INTEGER DEFAULT 0,
            sources     TEXT    DEFAULT '',
            error       TEXT    DEFAULT '',
            ts          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS error_log (
            id       SERIAL PRIMARY KEY,
            endpoint TEXT DEFAULT '',
            err_type TEXT DEFAULT '',
            message  TEXT DEFAULT '',
            tb       TEXT DEFAULT '',
            ts       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS blacklist (
            id      SERIAL PRIMARY KEY,
            pattern TEXT UNIQUE NOT NULL,
            ts      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS search_log (
            id    SERIAL PRIMARY KEY,
            query TEXT NOT NULL,
            ts    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS click_log (
            id        SERIAL PRIMARY KEY,
            deal_name TEXT NOT NULL,
            store     TEXT DEFAULT '',
            ts        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    con.commit()

    # Insert default config values (ON CONFLICT DO NOTHING keeps existing values)
    defaults = {
        'maintenance_mode': '0',
        'maintenance_msg':  'El sitio está temporalmente fuera de servicio. Volvemos pronto.',
        'cache_ttl':        '300',
        'source_steamspy':  '1',
        'source_ggdeals':   '1',
        'banner_active':    '0',
        'banner_text':      '',
        'carousel_pin':     '',
        'max_attempts':     '5',
        'lockout_minutes':  '15',
        'totp_secret':      '',
        'totp_enabled':     '0',
    }
    for k, v in defaults.items():
        cur.execute(
            "INSERT INTO admin_config (key, value) VALUES (%s, %s) ON CONFLICT (key) DO NOTHING",
            (k, v),
        )

    con.commit()
    con.close()


# ══ Config ════════════════════════════════════════════════════════════════════

def get_config(key: str, default: str = '') -> str:
    if time.time() - _cfg_cache_ts > _CFG_TTL or not _cfg_cache:
        _load_config_cache()
    return _cfg_cache.get(key, default)


def set_config(key: str, value: str):
    global _cfg_cache_ts
    con = _con()
    cur = con.cursor()
    cur.execute(
        "INSERT INTO admin_config (key, value) VALUES (%s, %s) "
        "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value",
        (key, str(value)),
    )
    con.commit()
    con.close()
    _cfg_cache_ts = 0.0  # invalidate so next read fetches from DB


def get_all_config() -> dict:
    if time.time() - _cfg_cache_ts > _CFG_TTL or not _cfg_cache:
        _load_config_cache()
    return dict(_cfg_cache)


# ══ Admin Activity Log ════════════════════════════════════════════════════════

def log_admin(action: str, detail: str = ''):
    con = _con()
    cur = con.cursor()
    cur.execute(
        "INSERT INTO admin_log (action, detail) VALUES (%s, %s)",
        (action, detail),
    )
    con.commit()
    con.close()


def get_admin_log(limit: int = 50) -> list:
    con = _con()
    cur = con.cursor()
    cur.execute(
        "SELECT id, action, detail, ts FROM admin_log ORDER BY id DESC LIMIT %s",
        (limit,),
    )
    rows = cur.fetchall()
    con.close()
    return [{'id': r[0], 'action': r[1], 'detail': r[2], 'ts': r[3]} for r in rows]


# ══ Login Attempts & IP Blocking ══════════════════════════════════════════════

def log_attempt(target: str, ip: str, success: bool):
    con = _con()
    cur = con.cursor()
    cur.execute(
        "INSERT INTO login_attempts (target, ip, success) VALUES (%s, %s, %s)",
        (target, ip, 1 if success else 0),
    )
    con.commit()
    con.close()


def is_ip_locked(ip: str) -> bool:
    max_attempts = int(get_config('max_attempts', '5'))
    lockout_min  = int(get_config('lockout_minutes', '15'))
    con = _con()
    cur = con.cursor()
    cur.execute("""
        SELECT COUNT(*) FROM login_attempts
        WHERE ip = %s AND success = 0
          AND ts > NOW() - (%s * INTERVAL '1 minute')
    """, (ip, lockout_min))
    count = cur.fetchone()[0]
    con.close()
    return count >= max_attempts


def get_login_attempts(limit: int = 50) -> list:
    con = _con()
    cur = con.cursor()
    cur.execute(
        "SELECT id, target, ip, success, ts FROM login_attempts ORDER BY id DESC LIMIT %s",
        (limit,),
    )
    rows = cur.fetchall()
    con.close()
    return [{'id': r[0], 'target': r[1], 'ip': r[2], 'success': bool(r[3]), 'ts': r[4]}
            for r in rows]


def get_blocked_ips() -> list:
    max_attempts = int(get_config('max_attempts', '5'))
    lockout_min  = int(get_config('lockout_minutes', '15'))
    con = _con()
    cur = con.cursor()
    cur.execute("""
        SELECT ip, COUNT(*) AS cnt, MAX(ts) AS last_ts
        FROM login_attempts
        WHERE success = 0
          AND ts > NOW() - (%s * INTERVAL '1 minute')
        GROUP BY ip
        HAVING COUNT(*) >= %s
        ORDER BY MAX(ts) DESC
    """, (lockout_min, max_attempts))
    rows = cur.fetchall()
    con.close()
    return [{'ip': r[0], 'count': r[1], 'last_ts': r[2]} for r in rows]


def unblock_ip(ip: str):
    con = _con()
    cur = con.cursor()
    cur.execute("DELETE FROM login_attempts WHERE ip = %s AND success = 0", (ip,))
    con.commit()
    con.close()


# ══ Cache History ═════════════════════════════════════════════════════════════

def log_cache_refresh(deals_count: int, duration_ms: int, sources: str, error: str = ''):
    con = _con()
    cur = con.cursor()
    cur.execute(
        "INSERT INTO cache_history (deals_count, duration_ms, sources, error) VALUES (%s, %s, %s, %s)",
        (deals_count, duration_ms, sources, error),
    )
    con.commit()
    con.close()


def get_cache_history(limit: int = 15) -> list:
    con = _con()
    cur = con.cursor()
    cur.execute(
        "SELECT id, deals_count, duration_ms, sources, error, ts "
        "FROM cache_history ORDER BY id DESC LIMIT %s",
        (limit,),
    )
    rows = cur.fetchall()
    con.close()
    result = []
    for r in rows:
        try:
            src = json.loads(r[3]) if r[3] else {}
        except Exception:
            src = {}
        result.append({
            'id': r[0], 'deals_count': r[1], 'duration_ms': r[2],
            'sources': src, 'error': r[4], 'ts': r[5],
        })
    return result


# ══ Server Error Log ══════════════════════════════════════════════════════════

def log_error(endpoint: str, err_type: str, message: str, tb: str = ''):
    con = _con()
    cur = con.cursor()
    cur.execute(
        "INSERT INTO error_log (endpoint, err_type, message, tb) VALUES (%s, %s, %s, %s)",
        (endpoint, err_type, message, tb[:5000]),
    )
    con.commit()
    con.close()


def get_error_log(limit: int = 20) -> list:
    con = _con()
    cur = con.cursor()
    cur.execute(
        "SELECT id, endpoint, err_type, message, tb, ts "
        "FROM error_log ORDER BY id DESC LIMIT %s",
        (limit,),
    )
    rows = cur.fetchall()
    con.close()
    return [{'id': r[0], 'endpoint': r[1], 'err_type': r[2],
             'message': r[3], 'tb': r[4], 'ts': r[5]} for r in rows]


def clear_error_log():
    con = _con()
    cur = con.cursor()
    cur.execute("DELETE FROM error_log")
    con.commit()
    con.close()


# ══ Title Blacklist ═══════════════════════════════════════════════════════════

def add_blacklist(pattern: str):
    con = _con()
    cur = con.cursor()
    cur.execute(
        "INSERT INTO blacklist (pattern) VALUES (%s) ON CONFLICT (pattern) DO NOTHING",
        (pattern.strip().lower(),),
    )
    con.commit()
    con.close()


def remove_blacklist(bl_id: int):
    con = _con()
    cur = con.cursor()
    cur.execute("DELETE FROM blacklist WHERE id = %s", (bl_id,))
    con.commit()
    con.close()


def get_blacklist() -> list:
    con = _con()
    cur = con.cursor()
    cur.execute("SELECT id, pattern, ts FROM blacklist ORDER BY id DESC")
    rows = cur.fetchall()
    con.close()
    return [{'id': r[0], 'pattern': r[1], 'ts': r[2]} for r in rows]


def is_blacklisted(name: str) -> bool:
    patterns = [r['pattern'] for r in get_blacklist()]
    name_l = name.strip().lower()
    return any(p in name_l for p in patterns)


# ══ Analytics ═════════════════════════════════════════════════════════════════

def log_search(query: str):
    if not query or len(query.strip()) < 2:
        return
    con = _con()
    cur = con.cursor()
    cur.execute("INSERT INTO search_log (query) VALUES (%s)", (query.strip().lower(),))
    con.commit()
    con.close()


def get_top_searches(limit: int = 20) -> list:
    con = _con()
    cur = con.cursor()
    cur.execute("""
        SELECT query, COUNT(*) AS cnt
        FROM search_log
        GROUP BY query
        ORDER BY cnt DESC
        LIMIT %s
    """, (limit,))
    rows = cur.fetchall()
    con.close()
    return [{'query': r[0], 'count': r[1]} for r in rows]


def log_click(deal_name: str, store: str):
    con = _con()
    cur = con.cursor()
    cur.execute(
        "INSERT INTO click_log (deal_name, store) VALUES (%s, %s)",
        (deal_name[:200], store[:100]),
    )
    con.commit()
    con.close()


def get_top_clicks(limit: int = 20) -> list:
    con = _con()
    cur = con.cursor()
    cur.execute("""
        SELECT deal_name, store, COUNT(*) AS cnt
        FROM click_log
        GROUP BY deal_name, store
        ORDER BY cnt DESC
        LIMIT %s
    """, (limit,))
    rows = cur.fetchall()
    con.close()
    return [{'deal_name': r[0], 'store': r[1], 'count': r[2]} for r in rows]


def get_store_click_stats() -> list:
    con = _con()
    cur = con.cursor()
    cur.execute("""
        SELECT store, COUNT(*) AS cnt
        FROM click_log
        WHERE store != ''
        GROUP BY store
        ORDER BY cnt DESC
        LIMIT 15
    """)
    rows = cur.fetchall()
    con.close()
    return [{'store': r[0], 'count': r[1]} for r in rows]
