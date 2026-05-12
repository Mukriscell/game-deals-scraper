import hmac
import os
import re
import secrets
import sqlite3

from werkzeug.security import check_password_hash, generate_password_hash

DB_PATH = os.path.join(os.path.dirname(__file__), "users.db")


def init_db():
    con = sqlite3.connect(DB_PATH)
    con.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            email      TEXT    UNIQUE NOT NULL,
            password   TEXT    NOT NULL,
            created_at TEXT    DEFAULT (datetime('now')),
            is_active  INTEGER DEFAULT 1,
            role       TEXT    DEFAULT 'user',
            last_seen  TEXT    DEFAULT NULL
        )
    """)
    # Migrations for existing DBs that predate these columns
    for col_def in [
        "is_active INTEGER DEFAULT 1",
        "role TEXT DEFAULT 'user'",
        "last_seen TEXT DEFAULT NULL",
    ]:
        try:
            con.execute(f"ALTER TABLE users ADD COLUMN {col_def}")
        except sqlite3.OperationalError:
            pass
    con.commit()
    con.close()


def validate_password(pw: str):
    """Returns an error string, or None if the password meets all requirements."""
    if len(pw) < 8:
        return "Mínimo 8 caracteres"
    if not re.search(r'[a-z]', pw):
        return "Debe incluir al menos una letra minúscula"
    if not re.search(r'[A-Z]', pw):
        return "Debe incluir al menos una letra mayúscula"
    if not re.search(r'\d', pw):
        return "Debe incluir al menos un número"
    if not re.search(r'[!@#$%^&*()\-_=+\[\]{}|;:\'",.<>?/\\]', pw):
        return "Debe incluir al menos un carácter especial (!@#$%...)"
    return None


def create_user(email: str, password: str):
    """Returns (success: bool, message: str)."""
    err = validate_password(password)
    if err:
        return False, err
    try:
        con = sqlite3.connect(DB_PATH)
        con.execute(
            "INSERT INTO users (email, password) VALUES (?, ?)",
            (email.lower().strip(), generate_password_hash(password)),
        )
        con.commit()
        con.close()
        return True, "Cuenta creada"
    except sqlite3.IntegrityError:
        return False, "Este correo ya está registrado"


def verify_user(email: str, password: str):
    """Returns user_id (int) if credentials are valid and account is active, else None."""
    con = sqlite3.connect(DB_PATH)
    row = con.execute(
        "SELECT id, password, is_active FROM users WHERE email = ?",
        (email.lower().strip(),),
    ).fetchone()
    con.close()
    if row and check_password_hash(row[1], password):
        if not row[2]:
            return None  # banned
        return row[0]
    return None


def verify_admin(email: str, password: str) -> bool:
    """Timing-safe comparison against ADMIN_EMAIL / ADMIN_PASSWORD env vars."""
    admin_email    = os.environ.get("ADMIN_EMAIL", "")
    admin_password = os.environ.get("ADMIN_PASSWORD", "")
    if not admin_email or not admin_password:
        return False
    email_ok    = hmac.compare_digest(email.lower().strip().encode(), admin_email.lower().encode())
    password_ok = hmac.compare_digest(password.encode(), admin_password.encode())
    return email_ok and password_ok


# ── User queries ──────────────────────────────────────────────────────────────

def get_all_users(page: int = 1, per_page: int = 20) -> tuple:
    """Returns (users_list, total_count, total_pages)."""
    offset = (page - 1) * per_page
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        "SELECT id, email, created_at, is_active, role, last_seen "
        "FROM users ORDER BY id LIMIT ? OFFSET ?",
        (per_page, offset),
    ).fetchall()
    total = con.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    con.close()
    total_pages = max(1, (total + per_page - 1) // per_page)
    return [dict(r) for r in rows], total, total_pages


def get_all_users_flat() -> list:
    """All users without pagination (for CSV export)."""
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        "SELECT id, email, created_at, is_active, role, last_seen FROM users ORDER BY id"
    ).fetchall()
    con.close()
    return [dict(r) for r in rows]


def get_user_counts() -> dict:
    """Returns total, active, moderator counts."""
    con = sqlite3.connect(DB_PATH)
    row = con.execute("""
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) AS active,
            SUM(CASE WHEN role = 'moderator' THEN 1 ELSE 0 END) AS moderators
        FROM users
    """).fetchone()
    con.close()
    return {'total': row[0], 'active': row[1] or 0, 'moderators': row[2] or 0}


def get_active_sessions(minutes: int = 60) -> list:
    """Users seen in the last N minutes."""
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    rows = con.execute("""
        SELECT id, email, role, last_seen
        FROM users
        WHERE is_active = 1
          AND last_seen IS NOT NULL
          AND datetime(last_seen) > datetime('now', ? || ' minutes')
        ORDER BY last_seen DESC
    """, (f'-{minutes}',)).fetchall()
    con.close()
    return [dict(r) for r in rows]


def update_user_last_seen(user_id: int):
    con = sqlite3.connect(DB_PATH)
    con.execute(
        "UPDATE users SET last_seen = datetime('now') WHERE id = ?",
        (user_id,),
    )
    con.commit()
    con.close()


def delete_user(user_id: int):
    con = sqlite3.connect(DB_PATH)
    con.execute("DELETE FROM users WHERE id = ?", (user_id,))
    con.commit()
    con.close()


def toggle_user_active(user_id: int):
    con = sqlite3.connect(DB_PATH)
    con.execute(
        "UPDATE users SET is_active = CASE WHEN is_active = 1 THEN 0 ELSE 1 END WHERE id = ?",
        (user_id,),
    )
    con.commit()
    con.close()


def set_user_role(user_id: int, role: str):
    if role not in ('user', 'moderator'):
        return
    con = sqlite3.connect(DB_PATH)
    con.execute("UPDATE users SET role = ? WHERE id = ?", (role, user_id))
    con.commit()
    con.close()


def email_exists(email: str) -> bool:
    con = sqlite3.connect(DB_PATH)
    row = con.execute(
        "SELECT id FROM users WHERE email = ?", (email.lower().strip(),)
    ).fetchone()
    con.close()
    return row is not None


def new_captcha():
    """Returns (question_str, answer_int)."""
    a = secrets.randbelow(10) + 1
    b = secrets.randbelow(10) + 1
    return f"¿Cuánto es {a} + {b}?", a + b


# ── Wishlist & Hidden Deals ────────────────────────────────────────────────────

def init_wishlist_tables():
    con = sqlite3.connect(DB_PATH)
    con.execute("""
        CREATE TABLE IF NOT EXISTS wishlist (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id       INTEGER NOT NULL,
            deal_name     TEXT    NOT NULL,
            deal_url      TEXT    NOT NULL DEFAULT '',
            deal_store    TEXT    NOT NULL DEFAULT '',
            deal_price    REAL    DEFAULT 0,
            deal_orig     REAL    DEFAULT 0,
            deal_disc     INTEGER DEFAULT 0,
            deal_thumb    TEXT    DEFAULT '',
            deal_currency TEXT    DEFAULT 'USD',
            ts            TEXT    DEFAULT (datetime('now')),
            UNIQUE(user_id, deal_name)
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS hidden_deals (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id      INTEGER NOT NULL,
            deal_name    TEXT    NOT NULL,
            hidden_until TEXT    NOT NULL,
            UNIQUE(user_id, deal_name)
        )
    """)
    con.commit()
    con.close()


def wishlist_add(user_id: int, deal: dict):
    con = sqlite3.connect(DB_PATH)
    try:
        con.execute("""
            INSERT OR REPLACE INTO wishlist
            (user_id, deal_name, deal_url, deal_store, deal_price,
             deal_orig, deal_disc, deal_thumb, deal_currency)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            (deal.get('name') or '')[:300],
            (deal.get('url') or '')[:500],
            (deal.get('store') or '')[:100],
            float(deal.get('price') or 0),
            float(deal.get('original_price') or 0),
            int(deal.get('discount') or 0),
            (deal.get('thumb') or '')[:500],
            (deal.get('currency') or 'USD')[:10],
        ))
        con.commit()
    finally:
        con.close()


def wishlist_remove(user_id: int, deal_name: str):
    con = sqlite3.connect(DB_PATH)
    con.execute(
        "DELETE FROM wishlist WHERE user_id = ? AND deal_name = ?",
        (user_id, deal_name),
    )
    con.commit()
    con.close()


def wishlist_toggle(user_id: int, deal: dict) -> bool:
    """Adds if absent, removes if present. Returns True if now in wishlist."""
    name = (deal.get('name') or '').strip()
    if not name:
        return False
    con = sqlite3.connect(DB_PATH)
    row = con.execute(
        "SELECT id FROM wishlist WHERE user_id = ? AND deal_name = ?",
        (user_id, name),
    ).fetchone()
    con.close()
    if row:
        wishlist_remove(user_id, name)
        return False
    wishlist_add(user_id, deal)
    return True


def wishlist_get(user_id: int) -> list:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    rows = con.execute("""
        SELECT id, deal_name, deal_url, deal_store, deal_price,
               deal_orig, deal_disc, deal_thumb, deal_currency, ts
        FROM wishlist WHERE user_id = ? ORDER BY ts DESC
    """, (user_id,)).fetchall()
    con.close()
    return [dict(r) for r in rows]


def wishlist_names(user_id: int) -> list:
    con = sqlite3.connect(DB_PATH)
    rows = con.execute(
        "SELECT deal_name FROM wishlist WHERE user_id = ?", (user_id,)
    ).fetchall()
    con.close()
    return [r[0] for r in rows]


def hide_deal(user_id: int, deal_name: str, hours: int = 1):
    con = sqlite3.connect(DB_PATH)
    con.execute("""
        INSERT OR REPLACE INTO hidden_deals (user_id, deal_name, hidden_until)
        VALUES (?, ?, datetime('now', ? || ' hours'))
    """, (user_id, (deal_name or '')[:300], str(hours)))
    con.commit()
    con.close()


def get_hidden_names(user_id: int) -> list:
    con = sqlite3.connect(DB_PATH)
    rows = con.execute("""
        SELECT deal_name FROM hidden_deals
        WHERE user_id = ? AND datetime(hidden_until) > datetime('now')
    """, (user_id,)).fetchall()
    con.close()
    return [r[0] for r in rows]


# ── Email Verification ────────────────────────────────────────────────────────

def init_email_verification_table():
    con = sqlite3.connect(DB_PATH)
    con.execute("""
        CREATE TABLE IF NOT EXISTS email_verifications (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            email      TEXT    UNIQUE NOT NULL,
            pwd_hash   TEXT    NOT NULL,
            code       TEXT    NOT NULL,
            expires_at TEXT    NOT NULL,
            sent_at    TEXT    DEFAULT (datetime('now'))
        )
    """)
    con.commit()
    con.close()


def generate_verification_code() -> str:
    return str(secrets.randbelow(900000) + 100000)


def get_verification(email: str):
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    row = con.execute(
        "SELECT * FROM email_verifications WHERE email = ?",
        (email.lower().strip(),),
    ).fetchone()
    con.close()
    return dict(row) if row else None


def store_verification(email: str, pwd_hash: str, code: str):
    """Upserts a pending verification (replaces any existing record for this email)."""
    con = sqlite3.connect(DB_PATH)
    con.execute("""
        INSERT OR REPLACE INTO email_verifications
        (email, pwd_hash, code, expires_at, sent_at)
        VALUES (?, ?, ?, datetime('now', '+30 minutes'), datetime('now'))
    """, (email.lower().strip(), pwd_hash, code))
    con.commit()
    con.close()


def verify_email_code(email: str, code: str):
    """
    Validates the code. On success creates the user account.
    Returns (True, user_id) or (False, error_message).
    """
    email = email.lower().strip()
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    row = con.execute("""
        SELECT *, (datetime('now') > expires_at) AS expired
        FROM email_verifications WHERE email = ?
    """, (email,)).fetchone()
    con.close()

    if not row:
        return False, 'No hay verificación pendiente. Regístrate de nuevo.'
    if row['expired']:
        return False, 'El código ha expirado. Solicita uno nuevo.'
    if row['code'] != code.strip():
        return False, 'Código incorrecto.'

    try:
        con = sqlite3.connect(DB_PATH)
        con.execute(
            "INSERT INTO users (email, password) VALUES (?, ?)",
            (email, row['pwd_hash']),
        )
        con.commit()
        uid = con.execute(
            "SELECT id FROM users WHERE email = ?", (email,)
        ).fetchone()[0]
        con.execute("DELETE FROM email_verifications WHERE email = ?", (email,))
        con.commit()
        con.close()
        return True, uid
    except sqlite3.IntegrityError:
        con.close()
        return False, 'Este correo ya está registrado.'


def can_resend(email: str) -> tuple:
    """Returns (can_resend: bool, wait_seconds: int)."""
    con = sqlite3.connect(DB_PATH)
    row = con.execute("""
        SELECT CAST((julianday('now') - julianday(sent_at)) * 86400 AS INTEGER)
        FROM email_verifications WHERE email = ?
    """, (email.lower().strip(),)).fetchone()
    con.close()
    if not row:
        return True, 0
    elapsed = row[0] or 0
    cooldown = 60
    if elapsed < cooldown:
        return False, cooldown - elapsed
    return True, 0


def delete_verification(email: str):
    con = sqlite3.connect(DB_PATH)
    con.execute(
        "DELETE FROM email_verifications WHERE email = ?", (email.lower().strip(),)
    )
    con.commit()
    con.close()
