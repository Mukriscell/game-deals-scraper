import functools
import io
import json
import os
import secrets
import time
import traceback
from concurrent.futures import ThreadPoolExecutor

from flask import (
    Flask, Response, render_template, redirect, request, session, url_for,
)

from auth import (
    can_resend, create_user, delete_user, delete_verification,
    email_exists, generate_verification_code, get_active_sessions, get_all_users,
    get_all_users_flat, get_hidden_names, get_user_counts, get_verification,
    hide_deal, init_db, init_email_verification_table, init_wishlist_tables,
    new_captcha, set_user_role, store_verification, toggle_user_active,
    update_user_last_seen, validate_password, verify_admin, verify_email_code,
    verify_user, wishlist_get, wishlist_names, wishlist_remove, wishlist_toggle,
)
from mail import is_configured as mail_is_configured, send_verification_email
from scraper import (
    scrape_deals, scrape_popular, scrape_rawg_popular, fetch_rawg_game_detail,
    scrape_subscriptions, scrape_steamspy_deals, scrape_ggdeals_deals,
    STREAMING_SERVICES, LEARNING_SERVICES,
)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
init_db()

from admin_db import init_admin_tables
init_admin_tables()
init_wishlist_tables()
init_email_verification_table()

# ── TOTP support ──────────────────────────────────────
try:
    import pyotp
    TOTP_AVAILABLE = True
except ImportError:
    TOTP_AVAILABLE = False

# ── Config sections used by /admin/config ─────────────
_CFG_SECTIONS = {
    'maintenance': ['maintenance_mode', 'maintenance_msg'],
    'banner':      ['banner_active', 'banner_text'],
    'carousel':    ['carousel_pin'],
    'sources':     ['source_steamspy', 'source_ggdeals', 'cache_ttl'],
    'limits':      ['max_attempts', 'lockout_minutes'],
}
_CHECKBOX_KEYS = {'maintenance_mode', 'source_steamspy', 'source_ggdeals', 'banner_active'}

# ── Cache ─────────────────────────────────────────────
_cache = {"deals": [], "featured": [], "subscriptions": [], "rawg": [], "ts": 0}
_rawg_detail_cache: dict = {}   # {name_lower: {"data": dict|None, "ts": float}}
CACHE_TTL_DEFAULT = 300


# ── Context processors ────────────────────────────────
@app.context_processor
def inject_user():
    return {"current_user": session.get("user_email")}


@app.context_processor
def inject_banner():
    from admin_db import get_config
    active = get_config('banner_active') == '1'
    return {
        'banner_active': active,
        'banner_text':   get_config('banner_text') if active else '',
    }


@app.context_processor
def inject_user_deal_data():
    uid = session.get('user_id')
    if not uid:
        return {'user_wishlist_names': '[]', 'user_hidden_names': '[]'}
    return {
        'user_wishlist_names': json.dumps(wishlist_names(uid)),
        'user_hidden_names':   json.dumps(get_hidden_names(uid)),
    }


# ── Admin decorator ───────────────────────────────────
def admin_required(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("is_admin"):
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return wrapper


# ── Middleware ────────────────────────────────────────
@app.before_request
def check_maintenance():
    from admin_db import get_config
    if get_config('maintenance_mode') != '1':
        return
    if session.get('is_admin'):
        return
    if request.path.startswith('/static') or request.path.startswith('/admin'):
        return
    msg = get_config('maintenance_msg', 'El sitio está temporalmente fuera de servicio.')
    return render_template('maintenance.html', msg=msg), 503


@app.before_request
def refresh_last_seen():
    uid = session.get('user_id')
    if uid:
        now = time.time()
        if now - session.get('_ls', 0) > 300:
            session['_ls'] = now
            update_user_last_seen(uid)


# ── Error handler ─────────────────────────────────────
@app.errorhandler(Exception)
def handle_exception(e):
    if app.debug:
        raise e
    from admin_db import log_error
    log_error(request.path, type(e).__name__, str(e), traceback.format_exc())
    return render_template('500.html'), 500


# ── Data fetching ─────────────────────────────────────
def get_data():
    from admin_db import (
        get_config, log_cache_refresh, is_blacklisted, log_error,
    )

    cache_ttl = int(get_config('cache_ttl', str(CACHE_TTL_DEFAULT)))
    if time.time() - _cache["ts"] < cache_ttl and _cache["deals"]:
        return _cache["deals"], _cache["featured"], _cache["subscriptions"]

    t0 = time.time()
    source_counts = {'ITAD': 0, 'SteamSpy': 0, 'GG.deals': 0}
    error_msg     = ''
    use_ss = get_config('source_steamspy', '1') == '1'
    use_gg = get_config('source_ggdeals', '1') == '1'

    try:
        with ThreadPoolExecutor(max_workers=5) as pool:
            f_deals   = pool.submit(scrape_deals, 5)
            f_popular = pool.submit(scrape_popular, 12)
            f_rawg    = pool.submit(scrape_rawg_popular, 20)
            f_ss      = pool.submit(scrape_steamspy_deals) if use_ss else None
            f_gg      = pool.submit(scrape_ggdeals_deals)  if use_gg else None
            deals    = f_deals.result()
            popular  = f_popular.result()
            rawg_list = f_rawg.result()
            ss_deals = f_ss.result() if f_ss else []
            gg_deals = f_gg.result() if f_gg else []
        source_counts['ITAD'] = len(deals)
    except Exception as exc:
        log_error('get_data', type(exc).__name__, str(exc), traceback.format_exc())
        error_msg = str(exc)
        deals = popular = ss_deals = gg_deals = rawg_list = []

    # Enrich carousel banners
    deal_banner = {d["id"]: d["thumb"] for d in deals if d.get("id") and d.get("thumb")}
    for game in popular:
        if game["id"] in deal_banner:
            game["banner"] = deal_banner[game["id"]]

    # Normalize SteamSpy store_id
    itad_steam_id = next((d["store_id"] for d in deals if d["store"] == "Steam"), "steam")
    for d in ss_deals:
        d["store_id"] = itad_steam_id

    # Merge sources
    seen = {d["name"].strip().lower() for d in deals}
    for d in ss_deals:
        key = d["name"].strip().lower()
        if key not in seen:
            deals.append(d)
            seen.add(key)
            source_counts['SteamSpy'] += 1
    for d in gg_deals:
        key = d["name"].strip().lower()
        if key not in seen:
            deals.append(d)
            seen.add(key)
            source_counts['GG.deals'] += 1
    print(f"[merge] ITAD:{source_counts['ITAD']} "
          f"+SS:{source_counts['SteamSpy']} +GG:{source_counts['GG.deals']} "
          f"(total: {len(deals)})")

    # Apply blacklist
    deals = [d for d in deals if not is_blacklisted(d['name'])]

    # Carousel pin
    carousel_pin = get_config('carousel_pin', '').strip()
    if carousel_pin:
        pin_l = carousel_pin.lower()
        pinned = next((d for d in deals if d['name'].strip().lower() == pin_l), None)
        if pinned:
            pf = {
                'id': pinned.get('id', ''),
                'title': pinned['name'],
                'price': pinned['price'],
                'banner': pinned.get('thumb', ''),
                'url': pinned['url'],
                'store': pinned.get('store', ''),
                'cut': pinned['discount'],
                'on_sale': True,
                'currency': pinned.get('currency', 'USD'),
            }
            popular = [f for f in popular if f.get('title', '').strip().lower() != pin_l]
            popular = [pf] + popular[:11]

    featured = popular

    # Subscriptions (ITAD IDs only)
    deal_ids = list({
        d["id"] for d in deals
        if d.get("id") and not d["id"].startswith(("steamspy_", "ggdeals_"))
    })
    sub_map = scrape_subscriptions(deal_ids) if deal_ids else {}

    subscriptions = [
        {"id": d["id"], "title": d["name"], "banner": d["thumb"],
         "itad_url": d["url"], "subs": sub_map[d["id"]]}
        for d in deals if d.get("id") and d["id"] in sub_map
    ]

    _cache.update({
        "deals": deals, "featured": featured,
        "subscriptions": subscriptions, "rawg": rawg_list, "ts": time.time(),
    })

    duration_ms = int((time.time() - t0) * 1000)
    log_cache_refresh(len(deals), duration_ms, json.dumps(source_counts), error_msg)

    return deals, featured, subscriptions


def sidebar_stats(deals, subscriptions):
    return {
        "games":      sum(1 for d in deals if d["category"] == "game"),
        "licenses":   len(LEARNING_SERVICES),
        "total_subs": len(STREAMING_SERVICES) + len(subscriptions),
    }


# ══ Public routes ══════════════════════════════════════════════════════════════

@app.route("/")
@app.route("/games")
def games():
    deals, featured, subscriptions = get_data()
    rawg_popular = _cache.get("rawg", [])
    sb = sidebar_stats(deals, subscriptions)
    game_deals = [d for d in deals if d["category"] == "game"]

    store_name_to_id = {d["store"]: d["store_id"] for d in game_deals if d["store"]}
    in_deals = {d["name"].strip().lower() for d in game_deals}
    for g in featured:
        if not g.get("on_sale") or not g.get("cut"):
            continue
        key = (g.get("title") or "").strip().lower()
        if key in in_deals:
            continue
        store_name = g.get("store") or ""
        orig = round(g["price"] / (1 - g["cut"] / 100), 2) if g["cut"] > 0 else g["price"]
        game_deals.append({
            "id": g["id"], "name": g["title"], "price": g["price"],
            "original_price": orig, "discount": g["cut"],
            "store": store_name,
            "store_id": store_name_to_id.get(store_name, store_name or "itad"),
            "url": g["url"], "thumb": g.get("banner") or "",
            "metacritic": 0, "steam_rating": 0,
            "store_low": 0.0, "history_low": 0.0,
            "flag": None, "expiry": None, "voucher": None,
            "currency": g.get("currency") or "USD", "category": "game",
        })
        in_deals.add(key)

    seen_stores = {}
    for d in game_deals:
        sid = d["store_id"]
        if sid not in seen_stores:
            seen_stores[sid] = d["store"]
    stores = [{"id": k, "name": v} for k, v in sorted(seen_stores.items(), key=lambda x: x[1])]

    stats = {
        **sb,
        "hot":  sum(1 for d in game_deals if d["discount"] >= 70),
        "free": sum(1 for d in game_deals if d["price"] == 0.0),
    }

    return render_template(
        "index.html",
        deals_json=json.dumps(game_deals, ensure_ascii=False),
        featured=featured, stores=stores, stats=stats, page="game",
        rawg_popular=rawg_popular,
    )


@app.route("/game/<path:name>")
def game_detail(name):
    name = name.strip()
    key  = name.lower()

    cached = _rawg_detail_cache.get(key)
    if cached and time.time() - cached["ts"] < 3600:
        game_data = cached["data"]
    else:
        game_data = fetch_rawg_game_detail(name)
        _rawg_detail_cache[key] = {"data": game_data, "ts": time.time()}

    if not game_data:
        deal = next((d for d in _cache.get("deals", [])
                     if d["name"].strip().lower() == key), None)
        return redirect(deal["url"] if deal else url_for("games"))

    deal = next((d for d in _cache.get("deals", [])
                 if d["name"].strip().lower() == key), None)
    return render_template("game_detail.html", game=game_data, deal=deal, page="game")


@app.route("/licencias")
def licencias():
    deals, _, subscriptions = get_data()
    sb = sidebar_stats(deals, subscriptions)
    cat_order  = ["courses", "ebooks", "software"]
    cat_labels = {
        "courses":  "📚 Cursos y Certificaciones",
        "ebooks":   "📖 Libros y Ebooks",
        "software": "💻 Software y Herramientas",
    }
    cat_map = {c: [] for c in cat_order}
    for svc in LEARNING_SERVICES:
        cat_map[svc["category"]].append(svc)
    return render_template(
        "licencias.html",
        cat_map=cat_map, cat_order=cat_order, cat_labels=cat_labels,
        stats={**sb, "total": len(LEARNING_SERVICES)}, page="license",
    )


@app.route("/suscripciones")
def suscripciones():
    deals, _, subscriptions = get_data()
    sb = sidebar_stats(deals, subscriptions)
    return render_template(
        "suscripciones.html",
        streaming=[s for s in STREAMING_SERVICES if s["category"] == "streaming"],
        gaming=[s for s in STREAMING_SERVICES if s["category"] == "gaming"],
        subscriptions=subscriptions,
        stats={**sb, "total": sb["total_subs"]}, page="subscription",
    )


_AUTH_STATS = {"games": 0, "licenses": 0, "total_subs": 0}


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("games"))

    error   = None
    success = request.args.get("registered") == "1"
    email   = ""

    if request.method == "POST":
        from admin_db import log_attempt, is_ip_locked
        ip = request.remote_addr or "unknown"

        if is_ip_locked(ip):
            error = "Demasiados intentos fallidos. Intenta más tarde."
        else:
            email    = request.form.get("email", "").strip()
            password = request.form.get("password", "")
            user_id  = verify_user(email, password)
            if user_id:
                log_attempt(email, ip, success=True)
                session["user_id"]    = user_id
                session["user_email"] = email.lower().strip()
                return redirect(url_for("games"))
            log_attempt(email, ip, success=False)
            error = "Correo o contraseña incorrectos"

    return render_template("login.html", error=error, success=success,
                           email=email, stats=_AUTH_STATS, page="")


def _mask_email(email: str) -> str:
    try:
        local, domain = email.rsplit('@', 1)
        return local[0] + '***@' + domain
    except Exception:
        return '***'


@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("games"))

    error = None
    email = ""

    if request.method == "POST":
        from werkzeug.security import generate_password_hash

        email     = request.form.get("email", "").strip().lower()
        password  = request.form.get("password", "")
        password2 = request.form.get("password2", "")
        captcha_i = request.form.get("captcha", "")

        try:
            if int(captcha_i) != session.get("captcha"):
                error = "Respuesta del captcha incorrecta"
        except (ValueError, TypeError):
            error = "Respuesta del captcha incorrecta"

        if not error and password != password2:
            error = "Las contraseñas no coinciden"

        if not error:
            pw_err = validate_password(password)
            if pw_err:
                error = pw_err

        if not error and not mail_is_configured():
            error = "El servicio de correo no está configurado. Contacta al administrador."

        if not error and email_exists(email):
            error = "Este correo ya está registrado."

        if not error:
            code     = generate_verification_code()
            pwd_hash = generate_password_hash(password)
            store_verification(email, pwd_hash, code)
            sent = send_verification_email(email, code)
            if not sent:
                delete_verification(email)
                error = "No pudimos enviar el correo. Revisa la dirección o inténtalo más tarde."
            else:
                session["reg_pending"] = email
                return redirect(url_for("verify_email"))

    captcha_q, captcha_a = new_captcha()
    session["captcha"] = captcha_a
    return render_template("register.html", error=error, email=email,
                           captcha_q=captcha_q, stats=_AUTH_STATS, page="")


@app.route("/verify-email", methods=["GET", "POST"])
def verify_email():
    email = session.get("reg_pending", "")
    if not email:
        return redirect(url_for("register"))

    error   = None
    success = None

    if request.method == "POST":
        code = "".join(request.form.get("code", "").split())  # strip spaces
        ok, result = verify_email_code(email, code)
        if ok:
            session.pop("reg_pending", None)
            session["user_id"]    = result
            session["user_email"] = email
            return redirect(url_for("games"))
        error = result

    return render_template(
        "verify_email.html",
        masked_email=_mask_email(email),
        error=error,
        success=success,
        stats=_AUTH_STATS,
        page="",
    )


@app.route("/verify-email/resend", methods=["POST"])
def verify_email_resend():
    email = session.get("reg_pending", "")
    if not email:
        return redirect(url_for("register"))

    ok, wait = can_resend(email)
    if not ok:
        return render_template(
            "verify_email.html",
            masked_email=_mask_email(email),
            error=f"Espera {wait} segundos antes de reenviar.",
            success=None,
            stats=_AUTH_STATS,
            page="",
        )

    rec = get_verification(email)
    if not rec:
        return redirect(url_for("register"))

    code = generate_verification_code()
    store_verification(email, rec["pwd_hash"], code)
    sent = send_verification_email(email, code)
    if not sent:
        return render_template(
            "verify_email.html",
            masked_email=_mask_email(email),
            error="No pudimos reenviar el correo. Inténtalo más tarde.",
            success=None,
            stats=_AUTH_STATS,
            page="",
        )

    return render_template(
        "verify_email.html",
        masked_email=_mask_email(email),
        error=None,
        success="Código reenviado. Revisa tu correo.",
        stats=_AUTH_STATS,
        page="",
    )


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("games"))


@app.route("/settings")
def settings_page():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    return render_template("settings.html", stats=_AUTH_STATS, page="")


# ── Analytics API (called from JS) ────────────────────
@app.route("/api/log/search", methods=["POST"])
def api_log_search():
    from admin_db import log_search
    data = request.get_json(silent=True) or {}
    log_search(data.get("query", ""))
    return "", 204


@app.route("/api/log/click", methods=["POST"])
def api_log_click():
    from admin_db import log_click
    data = request.get_json(silent=True) or {}
    log_click(data.get("name", ""), data.get("store", ""))
    return "", 204


# ══ Admin routes ══════════════════════════════════════════════════════════════

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if session.get("is_admin"):
        return redirect(url_for("admin_dashboard"))

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
                    return redirect(url_for("admin_2fa_verify"))
                session["is_admin"]    = True
                session["admin_email"] = email.lower().strip()
                log_admin("login", f"IP: {ip}")
                return redirect(url_for("admin_dashboard"))
            log_attempt("admin", ip, success=False)
            error = "Credenciales de administrador incorrectas"

    return render_template("admin/login.html", error=error)


@app.route("/admin/login/2fa", methods=["GET", "POST"])
def admin_2fa_verify():
    if not session.get("admin_2fa_pending"):
        return redirect(url_for("admin_login"))

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
                return redirect(url_for("admin_dashboard"))
        error = "Código inválido o expirado"

    return render_template("admin/2fa_verify.html", error=error)


@app.route("/admin/logout", methods=["POST"])
def admin_logout():
    from admin_db import log_admin
    log_admin("logout", session.get("admin_email", ""))
    session.pop("is_admin", None)
    session.pop("admin_email", None)
    return redirect(url_for("admin_login"))


@app.route("/admin")
@app.route("/admin/")
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

    # Per-source deal counts from last cache refresh
    hist = get_cache_history(1)
    source_counts = hist[0]['sources'] if hist else {}

    api_status = {
        "ITAD API":         {"configured": bool(os.environ.get("ITAD_API_KEY")),     "enabled": True,          "count": source_counts.get("ITAD", "—")},
        "SteamSpy API":     {"configured": True,                                      "enabled": config.get('source_steamspy') == '1', "count": source_counts.get("SteamSpy", "—")},
        "GG.deals API":     {"configured": bool(os.environ.get("GGDEALS_API_KEY")),  "enabled": config.get('source_ggdeals') == '1',  "count": source_counts.get("GG.deals", "—")},
        "ExchangeRate API": {"configured": bool(os.environ.get("EXCHANGERATE_API_KEY")), "enabled": True,       "count": "—"},
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


# ── Admin: user actions ───────────────────────────────

@app.route("/admin/users/<int:user_id>/delete", methods=["POST"])
@admin_required
def admin_delete_user(user_id):
    from admin_db import log_admin
    # get email before delete for log
    users_flat = get_all_users_flat()
    target = next((u['email'] for u in users_flat if u['id'] == user_id), str(user_id))
    delete_user(user_id)
    log_admin("delete_user", target)
    return redirect(url_for("admin_dashboard") + "?page=" + request.form.get("page", "1") + "#tab-users")


@app.route("/admin/users/<int:user_id>/toggle", methods=["POST"])
@admin_required
def admin_toggle_user(user_id):
    from admin_db import log_admin
    toggle_user_active(user_id)
    log_admin("toggle_user", str(user_id))
    return redirect(url_for("admin_dashboard") + "?page=" + request.form.get("page", "1") + "#tab-users")


@app.route("/admin/users/<int:user_id>/role", methods=["POST"])
@admin_required
def admin_set_role(user_id):
    from admin_db import log_admin
    role = request.form.get("role", "user")
    set_user_role(user_id, role)
    log_admin("set_role", f"user {user_id} → {role}")
    return redirect(url_for("admin_dashboard") + "?page=" + request.form.get("page", "1") + "#tab-users")


@app.route("/admin/users/export")
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


# ── Admin: cache ──────────────────────────────────────

@app.route("/admin/cache/refresh", methods=["POST"])
@admin_required
def admin_cache_refresh():
    from admin_db import log_admin
    _cache["ts"] = 0
    get_data()
    log_admin("cache_refresh", "forced")
    return redirect(url_for("admin_dashboard") + "#tab-overview")


# ── Admin: config ─────────────────────────────────────

@app.route("/admin/config", methods=["POST"])
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
        _cache['ts'] = 0  # force refresh with new TTL
    tab_map = {
        'maintenance': 'tab-content', 'banner': 'tab-content',
        'carousel': 'tab-content', 'sources': 'tab-config',
        'limits': 'tab-security',
    }
    tab = tab_map.get(section, "tab-config")
    return redirect(url_for("admin_dashboard") + f"?saved={section}#{tab}")


# ── Admin: blacklist ──────────────────────────────────

@app.route("/admin/blacklist/add", methods=["POST"])
@admin_required
def admin_blacklist_add():
    from admin_db import add_blacklist, log_admin
    pattern = request.form.get("pattern", "").strip()
    if pattern:
        add_blacklist(pattern)
        _cache["ts"] = 0  # invalidate so blacklist takes effect
        log_admin("blacklist_add", pattern)
    return redirect(url_for("admin_dashboard") + "#tab-content")


@app.route("/admin/blacklist/<int:bl_id>/remove", methods=["POST"])
@admin_required
def admin_blacklist_remove(bl_id):
    from admin_db import remove_blacklist, log_admin
    remove_blacklist(bl_id)
    _cache["ts"] = 0
    log_admin("blacklist_remove", str(bl_id))
    return redirect(url_for("admin_dashboard") + "#tab-content")


# ── Admin: blocked IPs ────────────────────────────────

@app.route("/admin/security/unblock", methods=["POST"])
@admin_required
def admin_unblock_ip():
    from admin_db import unblock_ip, log_admin
    ip = request.form.get("ip", "").strip()
    if ip:
        unblock_ip(ip)
        log_admin("unblock_ip", ip)
    return redirect(url_for("admin_dashboard") + "#tab-security")


# ── Admin: error log ──────────────────────────────────

@app.route("/admin/errors/clear", methods=["POST"])
@admin_required
def admin_clear_errors():
    from admin_db import clear_error_log, log_admin
    clear_error_log()
    log_admin("clear_error_log", "")
    return redirect(url_for("admin_dashboard") + "#tab-logs")


# ── Admin: 2FA ────────────────────────────────────────

@app.route("/admin/2fa/setup", methods=["POST"])
@admin_required
def admin_2fa_setup():
    from admin_db import set_config, log_admin
    if not TOTP_AVAILABLE:
        return redirect(url_for("admin_dashboard") + "#tab-security")
    secret = pyotp.random_base32()
    set_config("totp_secret", secret)
    set_config("totp_enabled", "0")
    log_admin("2fa_setup", "secret generated")
    return redirect(url_for("admin_dashboard") + "#tab-security")


@app.route("/admin/2fa/enable", methods=["POST"])
@admin_required
def admin_2fa_enable():
    from admin_db import get_config, set_config, log_admin
    if not TOTP_AVAILABLE:
        return redirect(url_for("admin_dashboard") + "#tab-security")
    code   = request.form.get("code", "").strip()
    secret = get_config("totp_secret", "")
    if secret:
        totp = pyotp.TOTP(secret)
        if totp.verify(code, valid_window=1):
            set_config("totp_enabled", "1")
            log_admin("2fa_enabled", "")
            return redirect(url_for("admin_dashboard") + "#tab-security")
    return redirect(url_for("admin_dashboard") + "#tab-security")


@app.route("/admin/2fa/disable", methods=["POST"])
@admin_required
def admin_2fa_disable():
    from admin_db import set_config, log_admin
    set_config("totp_enabled", "0")
    set_config("totp_secret", "")
    log_admin("2fa_disabled", "")
    return redirect(url_for("admin_dashboard") + "#tab-security")


# ── Wishlist & hide ───────────────────────────────────

@app.route('/api/wishlist/toggle', methods=['POST'])
def api_wishlist_toggle():
    uid = session.get('user_id')
    if not uid:
        return {'error': 'Debes iniciar sesión'}, 401
    data = request.get_json(silent=True) or {}
    in_wl = wishlist_toggle(uid, data)
    return {'in_wishlist': in_wl}


@app.route('/api/deals/hide', methods=['POST'])
def api_deal_hide():
    uid = session.get('user_id')
    if not uid:
        return '', 401
    data = request.get_json(silent=True) or {}
    name = (data.get('name') or '').strip()
    if name:
        hide_deal(uid, name)
    return '', 204


@app.route('/wishlist')
def user_wishlist():
    uid = session.get('user_id')
    if not uid:
        return redirect(url_for('login'))
    items = wishlist_get(uid)
    deals, _, subscriptions = get_data()
    sb = sidebar_stats(deals, subscriptions)
    return render_template('wishlist.html', items=items, stats=sb, page='wishlist')


@app.route('/wishlist/remove', methods=['POST'])
def user_wishlist_remove():
    uid = session.get('user_id')
    if not uid:
        return redirect(url_for('login'))
    name = (request.form.get('name') or '').strip()
    if name:
        wishlist_remove(uid, name)
    return redirect(url_for('user_wishlist'))


if __name__ == "__main__":
    app.run(debug=True)
