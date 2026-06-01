import hmac
import os
import re
import secrets

import psycopg2
import psycopg2.extras
from werkzeug.security import check_password_hash, generate_password_hash

from db import get_connection


def init_db():
    con = get_connection()
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id                   SERIAL PRIMARY KEY,
            email                TEXT    UNIQUE NOT NULL,
            password             TEXT    NOT NULL,
            created_at           TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active            INTEGER DEFAULT 1,
            role                 TEXT    DEFAULT 'user',
            last_seen            TIMESTAMP DEFAULT NULL,
            display_name         TEXT    DEFAULT NULL,
            phone                TEXT    DEFAULT NULL,
            email_notifications  INTEGER DEFAULT 1,
            avatar               TEXT    DEFAULT NULL
        )
    """)
    for col_def in [
        "is_active INTEGER DEFAULT 1",
        "role TEXT DEFAULT 'user'",
        "last_seen TIMESTAMP DEFAULT NULL",
        "display_name TEXT DEFAULT NULL",
        "phone TEXT DEFAULT NULL",
        "email_notifications INTEGER DEFAULT 1",
        "avatar TEXT DEFAULT NULL",
        "session_ver INTEGER DEFAULT 0",
        "newsletter INTEGER DEFAULT 0",
    ]:
        cur.execute(f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {col_def}")
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
    con = get_connection()
    try:
        cur = con.cursor()
        cur.execute(
            "INSERT INTO users (email, password) VALUES (%s, %s)",
            (email.lower().strip(), generate_password_hash(password)),
        )
        con.commit()
        return True, "Cuenta creada"
    except psycopg2.IntegrityError:
        con.rollback()
        return False, "Este correo ya está registrado"
    finally:
        con.close()


def verify_user(email: str, password: str):
    """Returns (user_id, display_name, avatar) if valid and active, else None."""
    con = get_connection()
    cur = con.cursor()
    cur.execute(
        "SELECT id, password, is_active, display_name, avatar FROM users WHERE email = %s",
        (email.lower().strip(),),
    )
    row = cur.fetchone()
    con.close()
    if row and check_password_hash(row[1], password):
        if not row[2]:
            return None  # banned
        return row[0], row[3], row[4]
    return None


def verify_admin(email: str, password: str) -> bool:
    """Compare against ADMIN_EMAIL and ADMIN_PASSWORD_HASH (preferred) or ADMIN_PASSWORD (legacy)."""
    admin_email = os.environ.get("ADMIN_EMAIL", "")
    if not admin_email:
        return False
    if not hmac.compare_digest(email.lower().strip().encode(), admin_email.lower().encode()):
        return False

    admin_hash = os.environ.get("ADMIN_PASSWORD_HASH", "")
    if admin_hash:
        return check_password_hash(admin_hash, password)

    admin_password = os.environ.get("ADMIN_PASSWORD", "")
    if not admin_password:
        return False
    return hmac.compare_digest(password.encode(), admin_password.encode())


# ── User queries ──────────────────────────────────────────────────────────────

def get_all_users(page: int = 1, per_page: int = 20) -> tuple:
    """Returns (users_list, total_count, total_pages)."""
    offset = (page - 1) * per_page
    con = get_connection()
    cur = con.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        "SELECT id, email, created_at, is_active, role, last_seen "
        "FROM users ORDER BY id LIMIT %s OFFSET %s",
        (per_page, offset),
    )
    rows = cur.fetchall()
    cur2 = con.cursor()
    cur2.execute("SELECT COUNT(*) FROM users")
    total = cur2.fetchone()[0]
    con.close()
    total_pages = max(1, (total + per_page - 1) // per_page)
    return [dict(r) for r in rows], total, total_pages


def get_all_users_flat() -> list:
    """All users without pagination (for CSV export)."""
    con = get_connection()
    cur = con.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        "SELECT id, email, created_at, is_active, role, last_seen FROM users ORDER BY id"
    )
    rows = cur.fetchall()
    con.close()
    return [dict(r) for r in rows]


def get_user_counts() -> dict:
    """Returns total, active, moderator counts."""
    con = get_connection()
    cur = con.cursor()
    cur.execute("""
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) AS active,
            SUM(CASE WHEN role = 'moderator' THEN 1 ELSE 0 END) AS moderators
        FROM users
    """)
    row = cur.fetchone()
    con.close()
    return {'total': row[0], 'active': row[1] or 0, 'moderators': row[2] or 0}


def get_active_sessions(minutes: int = 60) -> list:
    """Users seen in the last N minutes."""
    con = get_connection()
    cur = con.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT id, email, role, last_seen
        FROM users
        WHERE is_active = 1
          AND last_seen IS NOT NULL
          AND last_seen > NOW() - (%s * INTERVAL '1 minute')
        ORDER BY last_seen DESC
    """, (minutes,))
    rows = cur.fetchall()
    con.close()
    return [dict(r) for r in rows]


def update_user_last_seen(user_id: int):
    con = get_connection()
    cur = con.cursor()
    cur.execute(
        "UPDATE users SET last_seen = NOW() WHERE id = %s",
        (user_id,),
    )
    con.commit()
    con.close()


def delete_user(user_id: int, email: str):
    import glob
    con = get_connection()
    try:
        cur = con.cursor()
        cur.execute("DELETE FROM wishlist WHERE user_id = %s", (user_id,))
        cur.execute("DELETE FROM hidden_deals WHERE user_id = %s", (user_id,))
        cur.execute("DELETE FROM email_change_requests WHERE user_id = %s", (user_id,))
        cur.execute("DELETE FROM email_verifications WHERE email = %s", (email,))
        cur.execute("DELETE FROM password_resets WHERE email = %s", (email,))
        cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
        con.commit()
    finally:
        con.close()
    for f in glob.glob(f"static/uploads/avatars/{user_id}_*"):
        try:
            os.remove(f)
        except OSError:
            pass


def get_session_ver(user_id: int) -> int:
    con = get_connection()
    cur = con.cursor()
    cur.execute("SELECT session_ver FROM users WHERE id = %s", (user_id,))
    row = cur.fetchone()
    con.close()
    return row[0] if row else 0


def rotate_session_ver(user_id: int) -> int:
    con = get_connection()
    cur = con.cursor()
    cur.execute(
        "UPDATE users SET session_ver = session_ver + 1 WHERE id = %s RETURNING session_ver",
        (user_id,),
    )
    row = cur.fetchone()
    con.commit()
    con.close()
    return row[0] if row else 0


def toggle_user_active(user_id: int):
    con = get_connection()
    cur = con.cursor()
    cur.execute(
        "UPDATE users SET is_active = CASE WHEN is_active = 1 THEN 0 ELSE 1 END WHERE id = %s",
        (user_id,),
    )
    con.commit()
    con.close()


def set_user_role(user_id: int, role: str):
    if role not in ('user', 'moderator'):
        return
    con = get_connection()
    cur = con.cursor()
    cur.execute("UPDATE users SET role = %s WHERE id = %s", (role, user_id))
    con.commit()
    con.close()


def email_exists(email: str) -> bool:
    con = get_connection()
    cur = con.cursor()
    cur.execute("SELECT id FROM users WHERE email = %s", (email.lower().strip(),))
    row = cur.fetchone()
    con.close()
    return row is not None


def get_user_profile(user_id: int):
    con = get_connection()
    cur = con.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        "SELECT id, email, display_name, phone, email_notifications, avatar, last_seen, newsletter FROM users WHERE id = %s",
        (user_id,),
    )
    row = cur.fetchone()
    con.close()
    return dict(row) if row else None


def update_user_profile(user_id: int, display_name, phone, email_notifications: int):
    con = get_connection()
    cur = con.cursor()
    cur.execute(
        "UPDATE users SET display_name = %s, phone = %s, email_notifications = %s WHERE id = %s",
        (display_name or None, phone or None, email_notifications, user_id),
    )
    con.commit()
    con.close()


def update_user_avatar(user_id: int, avatar_filename: str):
    con = get_connection()
    cur = con.cursor()
    cur.execute("UPDATE users SET avatar = %s WHERE id = %s", (avatar_filename, user_id))
    con.commit()
    con.close()


def init_email_change_table():
    con = get_connection()
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS email_change_requests (
            id         SERIAL PRIMARY KEY,
            user_id    INTEGER NOT NULL UNIQUE,
            new_email  TEXT    NOT NULL,
            code       TEXT    NOT NULL,
            expires_at TIMESTAMP NOT NULL
        )
    """)
    con.commit()
    con.close()


def request_email_change(user_id: int, new_email: str, code: str):
    con = get_connection()
    cur = con.cursor()
    cur.execute("""
        INSERT INTO email_change_requests (user_id, new_email, code, expires_at)
        VALUES (%s, %s, %s, NOW() + INTERVAL '30 minutes')
        ON CONFLICT (user_id) DO UPDATE SET
            new_email  = EXCLUDED.new_email,
            code       = EXCLUDED.code,
            expires_at = EXCLUDED.expires_at
    """, (user_id, new_email.lower().strip(), code))
    con.commit()
    con.close()


def confirm_email_change(user_id: int, code: str):
    """Returns (True, new_email) on success or (False, error_message)."""
    con = get_connection()
    try:
        cur = con.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT *, (NOW() > expires_at) AS expired
            FROM email_change_requests WHERE user_id = %s
        """, (user_id,))
        row = cur.fetchone()
        if not row:
            return False, 'No hay cambio de correo pendiente.'
        if row['expired']:
            return False, 'El codigo ha expirado. Solicita uno nuevo.'
        if row['code'] != code.strip():
            return False, 'Codigo incorrecto.'
        new_email = row['new_email']
        cur2 = con.cursor()
        try:
            cur2.execute("UPDATE users SET email = %s WHERE id = %s", (new_email, user_id))
            cur2.execute("DELETE FROM email_change_requests WHERE user_id = %s", (user_id,))
            con.commit()
            return True, new_email
        except psycopg2.IntegrityError:
            con.rollback()
            return False, 'Este correo ya esta registrado por otra cuenta.'
    finally:
        con.close()


def new_captcha():
    """Returns (question_str, answer_int)."""
    a = secrets.randbelow(29) + 2   # 2–30
    b = secrets.randbelow(29) + 2   # 2–30
    return f"¿Cuánto es {a} + {b}?", a + b


# ── Wishlist & Hidden Deals ────────────────────────────────────────────────────

def init_wishlist_tables():
    con = get_connection()
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS wishlist (
            id            SERIAL PRIMARY KEY,
            user_id       INTEGER NOT NULL,
            deal_name     TEXT    NOT NULL,
            deal_url      TEXT    NOT NULL DEFAULT '',
            deal_store    TEXT    NOT NULL DEFAULT '',
            deal_price    DOUBLE PRECISION DEFAULT 0,
            deal_orig     DOUBLE PRECISION DEFAULT 0,
            deal_disc     INTEGER DEFAULT 0,
            deal_thumb    TEXT    DEFAULT '',
            deal_currency TEXT    DEFAULT 'USD',
            ts            TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, deal_name)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS hidden_deals (
            id           SERIAL PRIMARY KEY,
            user_id      INTEGER NOT NULL,
            deal_name    TEXT    NOT NULL,
            hidden_until TIMESTAMP NOT NULL,
            UNIQUE(user_id, deal_name)
        )
    """)
    for col_def in [
        "last_price DOUBLE PRECISION DEFAULT NULL",
        "notified_expiry INTEGER DEFAULT 0",
        "price_alert DOUBLE PRECISION DEFAULT NULL",
    ]:
        cur.execute(f"ALTER TABLE wishlist ADD COLUMN IF NOT EXISTS {col_def}")
    con.commit()
    con.close()


def wishlist_add(user_id: int, deal: dict):
    con = get_connection()
    try:
        cur = con.cursor()
        cur.execute("""
            INSERT INTO wishlist
            (user_id, deal_name, deal_url, deal_store, deal_price,
             deal_orig, deal_disc, deal_thumb, deal_currency)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (user_id, deal_name) DO UPDATE SET
                deal_url      = EXCLUDED.deal_url,
                deal_store    = EXCLUDED.deal_store,
                deal_price    = EXCLUDED.deal_price,
                deal_orig     = EXCLUDED.deal_orig,
                deal_disc     = EXCLUDED.deal_disc,
                deal_thumb    = EXCLUDED.deal_thumb,
                deal_currency = EXCLUDED.deal_currency
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
    con = get_connection()
    cur = con.cursor()
    cur.execute(
        "DELETE FROM wishlist WHERE user_id = %s AND deal_name = %s",
        (user_id, deal_name),
    )
    con.commit()
    con.close()


def wishlist_toggle(user_id: int, deal: dict) -> bool:
    """Adds if absent, removes if present. Returns True if now in wishlist."""
    name = (deal.get('name') or '').strip()
    if not name:
        return False
    con = get_connection()
    cur = con.cursor()
    cur.execute(
        "SELECT id FROM wishlist WHERE user_id = %s AND deal_name = %s",
        (user_id, name),
    )
    row = cur.fetchone()
    con.close()
    if row:
        wishlist_remove(user_id, name)
        return False
    wishlist_add(user_id, deal)
    return True


def wishlist_get(user_id: int) -> list:
    con = get_connection()
    cur = con.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT id, deal_name, deal_url, deal_store, deal_price,
               deal_orig, deal_disc, deal_thumb, deal_currency, ts, price_alert
        FROM wishlist WHERE user_id = %s ORDER BY ts DESC
    """, (user_id,))
    rows = cur.fetchall()
    con.close()
    return [dict(r) for r in rows]


def wishlist_set_alert(user_id: int, deal_name: str, price_alert):
    """Set or clear a price alert threshold. Pass None to clear."""
    con = get_connection()
    cur = con.cursor()
    cur.execute(
        "UPDATE wishlist SET price_alert = %s WHERE user_id = %s AND deal_name = %s",
        (price_alert, user_id, deal_name),
    )
    con.commit()
    con.close()


def wishlist_names(user_id: int) -> list:
    con = get_connection()
    cur = con.cursor()
    cur.execute("SELECT deal_name FROM wishlist WHERE user_id = %s", (user_id,))
    rows = cur.fetchall()
    con.close()
    return [r[0] for r in rows]


def hide_deal(user_id: int, deal_name: str, hours: int = 1):
    con = get_connection()
    cur = con.cursor()
    cur.execute("""
        INSERT INTO hidden_deals (user_id, deal_name, hidden_until)
        VALUES (%s, %s, NOW() + (%s * INTERVAL '1 hour'))
        ON CONFLICT (user_id, deal_name) DO UPDATE SET
            hidden_until = EXCLUDED.hidden_until
    """, (user_id, (deal_name or '')[:300], hours))
    con.commit()
    con.close()


def get_hidden_names(user_id: int) -> list:
    con = get_connection()
    cur = con.cursor()
    cur.execute("""
        SELECT deal_name FROM hidden_deals
        WHERE user_id = %s AND hidden_until > NOW()
    """, (user_id,))
    rows = cur.fetchall()
    con.close()
    return [r[0] for r in rows]


def get_wishlist_and_hidden_names(user_id: int) -> tuple:
    """Returns (wishlist_names, hidden_names) in a single DB connection."""
    con = get_connection()
    cur = con.cursor()
    cur.execute("SELECT deal_name FROM wishlist WHERE user_id = %s", (user_id,))
    wl = [r[0] for r in cur.fetchall()]
    cur.execute("""
        SELECT deal_name FROM hidden_deals
        WHERE user_id = %s AND hidden_until > NOW()
    """, (user_id,))
    hid = [r[0] for r in cur.fetchall()]
    con.close()
    return wl, hid


def get_all_user_deal_data(user_id: int) -> tuple:
    """Returns (wishlist_names, hidden_names, collection_names) in one connection."""
    con = get_connection()
    cur = con.cursor()
    cur.execute("SELECT deal_name FROM wishlist WHERE user_id = %s", (user_id,))
    wl = [r[0] for r in cur.fetchall()]
    cur.execute("""
        SELECT deal_name FROM hidden_deals
        WHERE user_id = %s AND hidden_until > NOW()
    """, (user_id,))
    hid = [r[0] for r in cur.fetchall()]
    cur.execute("SELECT deal_name FROM collections WHERE user_id = %s", (user_id,))
    col = [r[0] for r in cur.fetchall()]
    con.close()
    return wl, hid, col


# ── Collections ────────────────────────────────────────────────────────────────

def init_collections_table():
    con = get_connection()
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS collections (
            id         SERIAL PRIMARY KEY,
            user_id    INTEGER NOT NULL,
            deal_name  TEXT    NOT NULL,
            ts         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, deal_name)
        )
    """)
    con.commit()
    con.close()


def collection_toggle(user_id: int, deal_name: str) -> bool:
    """Adds if absent, removes if present. Returns True if now in collection."""
    name = (deal_name or '').strip()
    if not name:
        return False
    con = get_connection()
    cur = con.cursor()
    cur.execute(
        "SELECT id FROM collections WHERE user_id = %s AND deal_name = %s",
        (user_id, name),
    )
    row = cur.fetchone()
    con.close()
    if row:
        con2 = get_connection()
        cur2 = con2.cursor()
        cur2.execute("DELETE FROM collections WHERE user_id = %s AND deal_name = %s", (user_id, name))
        con2.commit()
        con2.close()
        return False
    con3 = get_connection()
    cur3 = con3.cursor()
    cur3.execute(
        "INSERT INTO collections (user_id, deal_name) VALUES (%s, %s) ON CONFLICT DO NOTHING",
        (user_id, name[:300]),
    )
    con3.commit()
    con3.close()
    return True


def collection_bulk_insert(user_id: int, names: list) -> int:
    """Insert many game names into collections at once. Returns count of newly added."""
    if not names:
        return 0
    con = get_connection()
    cur = con.cursor()
    added = 0
    for name in names:
        n = (name or '').strip()[:300]
        if not n:
            continue
        cur.execute(
            "INSERT INTO collections (user_id, deal_name) VALUES (%s, %s) ON CONFLICT DO NOTHING",
            (user_id, n),
        )
        added += cur.rowcount
    con.commit()
    con.close()
    return added


def collection_names(user_id: int) -> list:
    con = get_connection()
    cur = con.cursor()
    cur.execute("SELECT deal_name FROM collections WHERE user_id = %s", (user_id,))
    rows = cur.fetchall()
    con.close()
    return [r[0] for r in rows]


def get_newsletter_subscribers() -> list:
    """Returns list of {email} for users subscribed to newsletter."""
    con = get_connection()
    cur = con.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT email FROM users
        WHERE is_active = 1 AND newsletter = 1
        ORDER BY id
    """)
    rows = cur.fetchall()
    con.close()
    return [dict(r) for r in rows]


def update_newsletter_pref(user_id: int, enabled: bool):
    con = get_connection()
    cur = con.cursor()
    cur.execute(
        "UPDATE users SET newsletter = %s WHERE id = %s",
        (1 if enabled else 0, user_id),
    )
    con.commit()
    con.close()


def wishlist_get_all_with_emails() -> list:
    """Returns every wishlist row joined with user email, for notification checks."""
    con = get_connection()
    cur = con.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT w.id, w.user_id, w.deal_name, w.deal_price, w.deal_currency,
               w.last_price, w.notified_expiry, w.price_alert, u.email
        FROM wishlist w
        JOIN users u ON u.id = w.user_id
        WHERE u.is_active = 1
          AND (u.email_notifications IS NULL OR u.email_notifications = 1)
    """)
    rows = cur.fetchall()
    con.close()
    return [dict(r) for r in rows]


def wishlist_update_notification(item_id: int, last_price: float, notified_expiry: int):
    con = get_connection()
    cur = con.cursor()
    cur.execute(
        "UPDATE wishlist SET last_price = %s, notified_expiry = %s WHERE id = %s",
        (last_price, notified_expiry, item_id),
    )
    con.commit()
    con.close()


# ── Email Verification ────────────────────────────────────────────────────────

def init_email_verification_table():
    con = get_connection()
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS email_verifications (
            id         SERIAL PRIMARY KEY,
            email      TEXT      UNIQUE NOT NULL,
            pwd_hash   TEXT      NOT NULL,
            code       TEXT      NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            sent_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    con.commit()
    con.close()


def generate_verification_code() -> str:
    return str(secrets.randbelow(900000) + 100000)


def get_verification(email: str):
    con = get_connection()
    cur = con.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        "SELECT * FROM email_verifications WHERE email = %s",
        (email.lower().strip(),),
    )
    row = cur.fetchone()
    con.close()
    return dict(row) if row else None


def store_verification(email: str, pwd_hash: str, code: str):
    """Upserts a pending verification (replaces any existing record for this email)."""
    con = get_connection()
    cur = con.cursor()
    cur.execute("""
        INSERT INTO email_verifications (email, pwd_hash, code, expires_at, sent_at)
        VALUES (%s, %s, %s, NOW() + INTERVAL '30 minutes', NOW())
        ON CONFLICT (email) DO UPDATE SET
            pwd_hash   = EXCLUDED.pwd_hash,
            code       = EXCLUDED.code,
            expires_at = EXCLUDED.expires_at,
            sent_at    = EXCLUDED.sent_at
    """, (email.lower().strip(), pwd_hash, code))
    con.commit()
    con.close()


def verify_email_code(email: str, code: str):
    """
    Validates the code. On success creates the user account.
    Returns (True, user_id) or (False, error_message).
    """
    email = email.lower().strip()
    con = get_connection()
    try:
        cur = con.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT *, (NOW() > expires_at) AS expired
            FROM email_verifications WHERE email = %s
        """, (email,))
        row = cur.fetchone()

        if not row:
            return False, 'No hay verificación pendiente. Regístrate de nuevo.'
        if row['expired']:
            return False, 'El código ha expirado. Solicita uno nuevo.'
        if row['code'] != code.strip():
            return False, 'Código incorrecto.'

        try:
            cur2 = con.cursor()
            cur2.execute(
                "INSERT INTO users (email, password) VALUES (%s, %s)",
                (email, row['pwd_hash']),
            )
            cur2.execute("SELECT id FROM users WHERE email = %s", (email,))
            uid = cur2.fetchone()[0]
            cur2.execute("DELETE FROM email_verifications WHERE email = %s", (email,))
            con.commit()
            return True, uid
        except psycopg2.IntegrityError:
            con.rollback()
            return False, 'Este correo ya está registrado.'
    finally:
        con.close()


def can_resend(email: str) -> tuple:
    """Returns (can_resend: bool, wait_seconds: int)."""
    con = get_connection()
    cur = con.cursor()
    cur.execute("""
        SELECT EXTRACT(EPOCH FROM (NOW() - sent_at))::INTEGER
        FROM email_verifications WHERE email = %s
    """, (email.lower().strip(),))
    row = cur.fetchone()
    con.close()
    if not row:
        return True, 0
    elapsed = row[0] or 0
    cooldown = 60
    if elapsed < cooldown:
        return False, cooldown - elapsed
    return True, 0


def delete_verification(email: str):
    con = get_connection()
    cur = con.cursor()
    cur.execute(
        "DELETE FROM email_verifications WHERE email = %s", (email.lower().strip(),)
    )
    con.commit()
    con.close()


# ── Password Reset ─────────────────────────────────────────────────────────────

def init_password_reset_table():
    con = get_connection()
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS password_resets (
            id         SERIAL PRIMARY KEY,
            email      TEXT      UNIQUE NOT NULL,
            code       TEXT      NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            sent_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    con.commit()
    con.close()


def store_password_reset(email: str, code: str):
    con = get_connection()
    cur = con.cursor()
    cur.execute("""
        INSERT INTO password_resets (email, code, expires_at, sent_at)
        VALUES (%s, %s, NOW() + INTERVAL '15 minutes', NOW())
        ON CONFLICT (email) DO UPDATE SET
            code       = EXCLUDED.code,
            expires_at = EXCLUDED.expires_at,
            sent_at    = EXCLUDED.sent_at
    """, (email.lower().strip(), code))
    con.commit()
    con.close()


def verify_password_reset_code(email: str, code: str) -> tuple[bool, str]:
    email = email.lower().strip()
    con   = get_connection()
    try:
        cur = con.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT *, (NOW() > expires_at) AS expired
            FROM password_resets WHERE email = %s
        """, (email,))
        row = cur.fetchone()
        if not row:
            return False, "No se encontró una solicitud de recuperación para ese correo"
        if row["expired"]:
            return False, "El código ha expirado. Solicita uno nuevo"
        if not hmac.compare_digest(str(row["code"]), str(code)):
            return False, "Código incorrecto"
        return True, email
    finally:
        con.close()


def delete_password_reset(email: str):
    con = get_connection()
    cur = con.cursor()
    cur.execute("DELETE FROM password_resets WHERE email = %s", (email.lower().strip(),))
    con.commit()
    con.close()


def can_resend_reset(email: str) -> bool:
    """Returns True if at least 60 seconds have passed since the last reset code."""
    con = get_connection()
    cur = con.cursor()
    cur.execute("""
        SELECT EXTRACT(EPOCH FROM (NOW() - sent_at))::INTEGER
        FROM password_resets WHERE email = %s
    """, (email.lower().strip(),))
    row = cur.fetchone()
    con.close()
    if not row:
        return True
    return row[0] >= 60


def reset_user_password(email: str, new_password: str) -> tuple[bool, str]:
    err = validate_password(new_password)
    if err:
        return False, err
    email = email.lower().strip()
    con   = get_connection()
    try:
        cur = con.cursor()
        cur.execute(
            "UPDATE users SET password = %s WHERE email = %s",
            (generate_password_hash(new_password), email),
        )
        updated = cur.rowcount
        con.commit()
        if updated == 0:
            return False, "Usuario no encontrado"
        return True, "Contraseña actualizada"
    finally:
        con.close()
