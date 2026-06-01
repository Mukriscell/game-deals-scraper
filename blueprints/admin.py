import functools
import io
import os
import threading
import time

from flask import Blueprint, Response, redirect, render_template, request, session, url_for

from auth import (
    delete_user, get_active_sessions, get_all_users, get_all_users_flat,
    get_user_counts, set_user_role, toggle_user_active, verify_admin,
)
from cache import (
    _cache, _cache_lock, _do_refresh, CACHE_TTL_DEFAULT,
)
from extensions import limiter

try:
    import pyotp
    TOTP_AVAILABLE = True
except ImportError:
    TOTP_AVAILABLE = False

_CFG_SECTIONS = {
    'maintenance': ['maintenance_mode', 'maintenance_msg'],
    'banner':      ['banner_active', 'banner_text'],
    'carousel':    ['carousel_pin'],
    'sources':     ['source_steamspy', 'source_ggdeals', 'cache_ttl'],
    'limits':      ['max_attempts', 'lockout_minutes'],
}
_CHECKBOX_KEYS = {'maintenance_mode', 'source_steamspy', 'source_ggdeals', 'banner_active'}

bp = Blueprint('admin', __name__)


def admin_required(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("is_admin"):
            return redirect(url_for("admin.admin_login"))
        return f(*args, **kwargs)
    return wrapper


@bp.route("/admin/login", methods=["GET", "POST"])
@limiter.limit("10/minute; 30/hour")
def admin_login():
    if session.get("is_admin"):
        return redirect(url_for("admin.admin_dashboard"))

    error = None
    if request.method == "POST":
        from admin_db import log_attempt, is_ip_locked, log_admin, get_config
        ip = request.remote_addr or "unknown"

        if is_ip_locked(ip):
            error = "Demasiados intentos fallidos. Intenta más tarde."
        else:
            email    = request.form.get("email", "").strip()
            password = request.form.get("password", "")
            if verify_admin(email, password):
                log_attempt("admin", ip, success=True)
                if TOTP_AVAILABLE and get_config('totp_enabled') == '1':
                    session['admin_2fa_pending'] = True
                    session['admin_email_tmp']   = email.lower().strip()
                    return redirect(url_for("admin.admin_2fa_verify"))
                session["is_admin"]    = True
                session["admin_email"] = email.lower().strip()
                log_admin("login", f"IP: {ip}")
                return redirect(url_for("admin.admin_dashboard"))
            log_attempt("admin", ip, success=False)
            error = "Credenciales de administrador incorrectas"

    return render_template("admin/login.html", error=error)


@bp.route("/admin/login/2fa", methods=["GET", "POST"])
@limiter.limit("5/minute; 15/hour")
def admin_2fa_verify():
    if not session.get("admin_2fa_pending"):
        return redirect(url_for("admin.admin_login"))

    error = None
    if request.method == "POST":
        from admin_db import get_config, log_admin
        code   = request.form.get("code", "").strip()
        secret = get_config("totp_secret", "")
        if TOTP_AVAILABLE and secret:
            totp = pyotp.TOTP(secret)
            if totp.verify(code, valid_window=1):
                ip = request.remote_addr or "unknown"
                session.pop("admin_2fa_pending", None)
                session["is_admin"]    = True
                session["admin_email"] = session.pop("admin_email_tmp", "")
                log_admin("login_2fa", f"IP: {ip}")
                return redirect(url_for("admin.admin_dashboard"))
        error = "Código inválido o expirado"

    return render_template("admin/2fa_verify.html", error=error)


@bp.route("/admin/logout", methods=["POST"])
def admin_logout():
    from admin_db import log_admin
    log_admin("logout", session.get("admin_email", ""))
    session.pop("is_admin", None)
    session.pop("admin_email", None)
    return redirect(url_for("admin.admin_login"))


@bp.route("/admin")
@bp.route("/admin/")
@admin_required
def admin_dashboard():
    from admin_db import (
        get_config, get_all_config, get_admin_log, get_error_log,
        get_cache_history, get_login_attempts, get_blocked_ips,
        get_blacklist, get_top_searches, get_top_clicks, get_store_click_stats,
    )

    page = request.args.get("page", 1, type=int)
    users, user_total, user_total_pages = get_all_users(page=page, per_page=20)
    counts = get_user_counts()

    now       = time.time()
    cache_age = (now - _cache["ts"]) if _cache["ts"] else None
    cache_ttl = int(get_config('cache_ttl', str(CACHE_TTL_DEFAULT)))

    config = get_all_config()
    hist   = get_cache_history(1)
    source_counts = hist[0]['sources'] if hist else {}

    api_status = {
        "ITAD API":         {"configured": bool(os.environ.get("ITAD_API_KEY")),            "enabled": True,                              "count": source_counts.get("ITAD", "—")},
        "SteamSpy API":     {"configured": True,                                             "enabled": config.get('source_steamspy') == '1', "count": source_counts.get("SteamSpy", "—")},
        "GG.deals API":     {"configured": bool(os.environ.get("GGDEALS_API_KEY")),         "enabled": config.get('source_ggdeals') == '1',  "count": source_counts.get("GG.deals", "—")},
        "ExchangeRate API": {"configured": bool(os.environ.get("EXCHANGERATE_API_KEY")),    "enabled": True,                              "count": "—"},
    }

    totp_uri = None
    if TOTP_AVAILABLE and config.get('totp_secret') and config.get('totp_enabled') == '0':
        totp_uri = pyotp.TOTP(config['totp_secret']).provisioning_uri(
            name=session.get('admin_email', 'admin'),
            issuer_name='GAMEDEALS Admin',
        )

    return render_template(
        "admin/dashboard.html",
        users=users,
        user_total=user_total,
        user_page=page,
        user_total_pages=user_total_pages,
        user_counts=counts,
        active_sessions=get_active_sessions(60),
        cache_age=cache_age,
        cache_ttl=cache_ttl,
        deals_count=len(_cache["deals"]),
        cache_history=get_cache_history(15),
        config=config,
        api_status=api_status,
        top_searches=get_top_searches(20),
        top_clicks=get_top_clicks(20),
        store_stats=get_store_click_stats(),
        admin_log=get_admin_log(50),
        error_log=get_error_log(20),
        login_attempts=get_login_attempts(30),
        blocked_ips=get_blocked_ips(),
        blacklist=get_blacklist(),
        admin_email=session.get("admin_email", ""),
        totp_available=TOTP_AVAILABLE,
        totp_uri=totp_uri,
    )


# ── User actions ──────────────────────────────────────────────────────────────

@bp.route("/admin/users/<int:user_id>/delete", methods=["POST"])
@admin_required
def admin_delete_user(user_id):
    from admin_db import log_admin
    users_flat = get_all_users_flat()
    target = next((u['email'] for u in users_flat if u['id'] == user_id), str(user_id))
    delete_user(user_id)
    log_admin("delete_user", target)
    return redirect(url_for("admin.admin_dashboard") + "?page=" + request.form.get("page", "1") + "#tab-users")


@bp.route("/admin/users/<int:user_id>/toggle", methods=["POST"])
@admin_required
def admin_toggle_user(user_id):
    from admin_db import log_admin
    toggle_user_active(user_id)
    log_admin("toggle_user", str(user_id))
    return redirect(url_for("admin.admin_dashboard") + "?page=" + request.form.get("page", "1") + "#tab-users")


@bp.route("/admin/users/<int:user_id>/role", methods=["POST"])
@admin_required
def admin_set_role(user_id):
    from admin_db import log_admin
    role = request.form.get("role", "user")
    set_user_role(user_id, role)
    log_admin("set_role", f"user {user_id} → {role}")
    return redirect(url_for("admin.admin_dashboard") + "?page=" + request.form.get("page", "1") + "#tab-users")


@bp.route("/admin/users/export")
@admin_required
def admin_export_users():
    from admin_db import log_admin
    users = get_all_users_flat()
    log_admin("export_users", f"{len(users)} users")

    def generate():
        yield "id,email,created_at,is_active,role,last_seen\n"
        for u in users:
            yield (f"{u['id']},{u['email']},{u['created_at']},"
                   f"{u['is_active']},{u['role']},{u['last_seen'] or ''}\n")

    return Response(
        generate(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=users.csv"},
    )


# ── Newsletter ────────────────────────────────────────────────────────────────

@bp.route("/admin/newsletter/send", methods=["POST"])
@admin_required
def admin_newsletter_send():
    from admin_db import log_admin
    from cache import _do_newsletter
    threading.Thread(target=_do_newsletter, daemon=True).start()
    log_admin("newsletter_send", "manual trigger")
    return redirect(url_for("admin.admin_dashboard") + "#tab-overview")


# ── Cache ─────────────────────────────────────────────────────────────────────

@bp.route("/admin/cache/refresh", methods=["POST"])
@admin_required
def admin_cache_refresh():
    from admin_db import log_admin
    with _cache_lock:
        _cache["ts"] = 0
        if not _cache["refreshing"]:
            _cache["refreshing"] = True
            threading.Thread(target=_do_refresh, daemon=True).start()
    log_admin("cache_refresh", "forced")
    return redirect(url_for("admin.admin_dashboard") + "#tab-overview")


# ── Config ────────────────────────────────────────────────────────────────────

@bp.route("/admin/config", methods=["POST"])
@admin_required
def admin_save_config():
    from admin_db import set_config, log_admin
    section = request.form.get("_section", "")
    keys    = _CFG_SECTIONS.get(section, [])
    changed = []
    for key in keys:
        if key in _CHECKBOX_KEYS:
            val = '1' if key in request.form else '0'
        else:
            val = request.form.get(key, '').strip()
        set_config(key, val)
        changed.append(key)
    if changed:
        log_admin("config_update", f"[{section}] {', '.join(changed)}")
    if 'cache_ttl' in changed:
        _cache['ts'] = 0
    tab_map = {
        'maintenance': 'tab-content', 'banner': 'tab-content',
        'carousel': 'tab-content', 'sources': 'tab-config',
        'limits': 'tab-security',
    }
    tab = tab_map.get(section, "tab-config")
    return redirect(url_for("admin.admin_dashboard") + f"?saved={section}#{tab}")


# ── Blacklist ─────────────────────────────────────────────────────────────────

@bp.route("/admin/blacklist/add", methods=["POST"])
@admin_required
def admin_blacklist_add():
    from admin_db import add_blacklist, log_admin
    pattern = request.form.get("pattern", "").strip()
    if pattern:
        add_blacklist(pattern)
        _cache["ts"] = 0
        log_admin("blacklist_add", pattern)
    return redirect(url_for("admin.admin_dashboard") + "#tab-content")


@bp.route("/admin/blacklist/<int:bl_id>/remove", methods=["POST"])
@admin_required
def admin_blacklist_remove(bl_id):
    from admin_db import remove_blacklist, log_admin
    remove_blacklist(bl_id)
    _cache["ts"] = 0
    log_admin("blacklist_remove", str(bl_id))
    return redirect(url_for("admin.admin_dashboard") + "#tab-content")


# ── Blocked IPs ───────────────────────────────────────────────────────────────

@bp.route("/admin/security/unblock", methods=["POST"])
@admin_required
def admin_unblock_ip():
    from admin_db import unblock_ip, log_admin
    ip = request.form.get("ip", "").strip()
    if ip:
        unblock_ip(ip)
        log_admin("unblock_ip", ip)
    return redirect(url_for("admin.admin_dashboard") + "#tab-security")


# ── Error log ─────────────────────────────────────────────────────────────────

@bp.route("/admin/errors/clear", methods=["POST"])
@admin_required
def admin_clear_errors():
    from admin_db import clear_error_log, log_admin
    clear_error_log()
    log_admin("clear_error_log", "")
    return redirect(url_for("admin.admin_dashboard") + "#tab-logs")


# ── 2FA ───────────────────────────────────────────────────────────────────────

@bp.route("/admin/2fa/setup", methods=["POST"])
@admin_required
def admin_2fa_setup():
    from admin_db import set_config, log_admin
    if not TOTP_AVAILABLE:
        return redirect(url_for("admin.admin_dashboard") + "#tab-security")
    secret = pyotp.random_base32()
    set_config("totp_secret", secret)
    set_config("totp_enabled", "0")
    log_admin("2fa_setup", "secret generated")
    return redirect(url_for("admin.admin_dashboard") + "#tab-security")


@bp.route("/admin/2fa/enable", methods=["POST"])
@admin_required
def admin_2fa_enable():
    from admin_db import get_config, set_config, log_admin
    if not TOTP_AVAILABLE:
        return redirect(url_for("admin.admin_dashboard") + "#tab-security")
    code   = request.form.get("code", "").strip()
    secret = get_config("totp_secret", "")
    if secret:
        totp = pyotp.TOTP(secret)
        if totp.verify(code, valid_window=1):
            set_config("totp_enabled", "1")
            log_admin("2fa_enabled", "")
            return redirect(url_for("admin.admin_dashboard") + "#tab-security")
    return redirect(url_for("admin.admin_dashboard") + "#tab-security")


@bp.route("/admin/2fa/disable", methods=["POST"])
@admin_required
def admin_2fa_disable():
    from admin_db import set_config, log_admin
    set_config("totp_enabled", "0")
    set_config("totp_secret", "")
    log_admin("2fa_disabled", "")
    return redirect(url_for("admin.admin_dashboard") + "#tab-security")
