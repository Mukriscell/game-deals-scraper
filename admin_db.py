"""
admin_db.py — All admin-specific database tables and helpers.
All data lives in the same SQLite file as auth.py (users.db).
"""
import json
import sqlite3

from auth import DB_PATH


def _con():
    return sqlite3.connect(DB_PATH)


# ══ Init ══════════════════════════════════════════════════════════════════════

def init_admin_tables():
    con = _con()

    con.execute("""
        CREATE TABLE IF NOT EXISTS admin_config (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL DEFAULT ''
        )
    """)

    con.execute("""
        CREATE TABLE IF NOT EXISTS admin_log (
            id     INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            detail TEXT NOT NULL DEFAULT '',
            ts     TEXT DEFAULT (datetime('now'))
        )
    """)

    con.execute("""
        CREATE TABLE IF NOT EXISTS login_attempts (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            target  TEXT NOT NULL,
            ip      TEXT NOT NULL DEFAULT '',
            success INTEGER DEFAULT 0,
            ts      TEXT DEFAULT (datetime('now'))
        )
    """)

    con.execute("""
        CREATE TABLE IF NOT EXISTS cache_history (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            deals_count INTEGER DEFAULT 0,
            duration_ms INTEGER DEFAULT 0,
            sources     TEXT    DEFAULT '',
            error       TEXT    DEFAULT '',
            ts          TEXT    DEFAULT (datetime('now'))
        )
    """)

    con.execute("""
        CREATE TABLE IF NOT EXISTS error_log (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            endpoint TEXT DEFAULT '',
            err_type TEXT DEFAULT '',
            message  TEXT DEFAULT '',
            tb       TEXT DEFAULT '',
            ts       TEXT DEFAULT (datetime('now'))
        )
    """)

    con.execute("""
        CREATE TABLE IF NOT EXISTS blacklist (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            pattern TEXT UNIQUE NOT NULL,
            ts      TEXT DEFAULT (datetime('now'))
        )
    """)

    con.execute("""
        CREATE TABLE IF NOT EXISTS search_log (
            id    INTEGER PRIMARY KEY AUTOINCREMENT,
            query TEXT NOT NULL,
            ts    TEXT DEFAULT (datetime('now'))
        )
    """)

    con.execute("""
        CREATE TABLE IF NOT EXISTS click_log (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            deal_name TEXT NOT NULL,
            store     TEXT DEFAULT '',
            ts        TEXT DEFAULT (datetime('now'))
        )
    """)

    con.commit()

    # Insert default config values (INSERT OR IGNORE keeps existing values)
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
        con.execute("INSERT OR IGNORE INTO admin_config (key, value) VALUES (?, ?)", (k, v))

    con.commit()
    con.close()


# ══ Config ════════════════════════════════════════════════════════════════════

def get_config(key: str, default: str = '') -> str:
    con = _con()
    row = con.execute("SELECT value FROM admin_config WHERE key = ?", (key,)).fetchone()
    con.close()
    return row[0] if row else default


def set_config(key: str, value: str):
    con = _con()
    con.execute(
        "INSERT OR REPLACE INTO admin_config (key, value) VALUES (?, ?)",
        (key, str(value)),
    )
    con.commit()
    con.close()


def get_all_config() -> dict:
    con = _con()
    rows = con.execute("SELECT key, value FROM admin_config").fetchall()
    con.close()
    return {r[0]: r[1] for r in rows}


# ══ Admin Activity Log ════════════════════════════════════════════════════════

def log_admin(action: str, detail: str = ''):
    con = _con()
    con.execute(
        "INSERT INTO admin_log (action, detail) VALUES (?, ?)",
        (action, detail),
    )
    con.commit()
    con.close()


def get_admin_log(limit: int = 50) -> list:
    con = _con()
    rows = con.execute(
        "SELECT id, action, detail, ts FROM admin_log ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    con.close()
    return [{'id': r[0], 'action': r[1], 'detail': r[2], 'ts': r[3]} for r in rows]


# ══ Login Attempts & IP Blocking ══════════════════════════════════════════════

def log_attempt(target: str, ip: str, success: bool):
    con = _con()
    con.execute(
        "INSERT INTO login_attempts (target, ip, success) VALUES (?, ?, ?)",
        (target, ip, 1 if success else 0),
    )
    con.commit()
    con.close()


def is_ip_locked(ip: str) -> bool:
    max_attempts = int(get_config('max_attempts', '5'))
    lockout_min  = int(get_config('lockout_minutes', '15'))
    con = _con()
    count = con.execute("""
        SELECT COUNT(*) FROM login_attempts
        WHERE ip = ? AND success = 0
          AND ts > datetime('now', ? || ' minutes')
    """, (ip, f'-{lockout_min}')).fetchone()[0]
    con.close()
    return count >= max_attempts


def get_login_attempts(limit: int = 50) -> list:
    con = _con()
    rows = con.execute(
        "SELECT id, target, ip, success, ts FROM login_attempts ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    con.close()
    return [{'id': r[0], 'target': r[1], 'ip': r[2], 'success': bool(r[3]), 'ts': r[4]}
            for r in rows]


def get_blocked_ips() -> list:
    max_attempts = int(get_config('max_attempts', '5'))
    lockout_min  = int(get_config('lockout_minutes', '15'))
    con = _con()
    rows = con.execute("""
        SELECT ip, COUNT(*) AS cnt, MAX(ts) AS last_ts
        FROM login_attempts
        WHERE success = 0
          AND ts > datetime('now', ? || ' minutes')
        GROUP BY ip
        HAVING cnt >= ?
        ORDER BY last_ts DESC
    """, (f'-{lockout_min}', max_attempts)).fetchall()
    con.close()
    return [{'ip': r[0], 'count': r[1], 'last_ts': r[2]} for r in rows]


def unblock_ip(ip: str):
    con = _con()
    con.execute("DELETE FROM login_attempts WHERE ip = ? AND success = 0", (ip,))
    con.commit()
    con.close()


# ══ Cache History ═════════════════════════════════════════════════════════════

def log_cache_refresh(deals_count: int, duration_ms: int, sources: str, error: str = ''):
    con = _con()
    con.execute(
        "INSERT INTO cache_history (deals_count, duration_ms, sources, error) VALUES (?, ?, ?, ?)",
        (deals_count, duration_ms, sources, error),
    )
    con.commit()
    con.close()


def get_cache_history(limit: int = 15) -> list:
    con = _con()
    rows = con.execute(
        "SELECT id, deals_count, duration_ms, sources, error, ts "
        "FROM cache_history ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
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
    con.execute(
        "INSERT INTO error_log (endpoint, err_type, message, tb) VALUES (?, ?, ?, ?)",
        (endpoint, err_type, message, tb[:5000]),
    )
    con.commit()
    con.close()


def get_error_log(limit: int = 20) -> list:
    con = _con()
    rows = con.execute(
        "SELECT id, endpoint, err_type, message, tb, ts "
        "FROM error_log ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    con.close()
    return [{'id': r[0], 'endpoint': r[1], 'err_type': r[2],
             'message': r[3], 'tb': r[4], 'ts': r[5]} for r in rows]


def clear_error_log():
    con = _con()
    con.execute("DELETE FROM error_log")
    con.commit()
    con.close()


# ══ Title Blacklist ═══════════════════════════════════════════════════════════

def add_blacklist(pattern: str):
    con = _con()
    try:
        con.execute("INSERT INTO blacklist (pattern) VALUES (?)", (pattern.strip().lower(),))
        con.commit()
    except sqlite3.IntegrityError:
        pass
    con.close()


def remove_blacklist(bl_id: int):
    con = _con()
    con.execute("DELETE FROM blacklist WHERE id = ?", (bl_id,))
    con.commit()
    con.close()


def get_blacklist() -> list:
    con = _con()
    rows = con.execute(
        "SELECT id, pattern, ts FROM blacklist ORDER BY id DESC"
    ).fetchall()
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
    con.execute("INSERT INTO search_log (query) VALUES (?)", (query.strip().lower(),))
    con.commit()
    con.close()


def get_top_searches(limit: int = 20) -> list:
    con = _con()
    rows = con.execute("""
        SELECT query, COUNT(*) AS cnt
        FROM search_log
        GROUP BY query
        ORDER BY cnt DESC
        LIMIT ?
    """, (limit,)).fetchall()
    con.close()
    return [{'query': r[0], 'count': r[1]} for r in rows]


def log_click(deal_name: str, store: str):
    con = _con()
    con.execute(
        "INSERT INTO click_log (deal_name, store) VALUES (?, ?)",
        (deal_name[:200], store[:100]),
    )
    con.commit()
    con.close()


def get_top_clicks(limit: int = 20) -> list:
    con = _con()
    rows = con.execute("""
        SELECT deal_name, store, COUNT(*) AS cnt
        FROM click_log
        GROUP BY deal_name, store
        ORDER BY cnt DESC
        LIMIT ?
    """, (limit,)).fetchall()
    con.close()
    return [{'deal_name': r[0], 'store': r[1], 'count': r[2]} for r in rows]


def get_store_click_stats() -> list:
    con = _con()
    rows = con.execute("""
        SELECT store, COUNT(*) AS cnt
        FROM click_log
        WHERE store != ''
        GROUP BY store
        ORDER BY cnt DESC
        LIMIT 15
    """).fetchall()
    con.close()
    return [{'store': r[0], 'count': r[1]} for r in rows]
