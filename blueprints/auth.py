import secrets
import time

from flask import Blueprint, redirect, render_template, request, session, url_for

from auth import (
    can_resend, create_user, delete_verification, email_exists,
    generate_verification_code, get_session_ver, get_verification,
    get_wishlist_and_hidden_names, init_password_reset_table, new_captcha,
    can_resend_reset, store_password_reset, verify_password_reset_code,
    delete_password_reset, reset_user_password,
    store_verification, validate_password, verify_email_code, verify_user,
)
from extensions import limiter
from mail import (
    is_configured as mail_is_configured,
    send_verification_email,
    send_password_reset_email,
)
from utils import is_valid_email, mask_email

bp = Blueprint('auth', __name__)


@bp.route("/login", methods=["GET", "POST"])
@limiter.limit("20/minute; 100/hour")
def login():
    if session.get("user_id"):
        return redirect(url_for("games.games"))

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
            result   = verify_user(email, password)
            if result:
                user_id, display_name, avatar = result
                log_attempt(email, ip, success=True)
                wl, hid = get_wishlist_and_hidden_names(user_id)
                now = time.time()
                session.clear()
                session["user_id"]           = user_id
                session["user_email"]        = email.lower().strip()
                session["user_display_name"] = display_name
                session["user_avatar"]       = avatar
                session["_wl"]               = wl
                session["_wl_ts"]            = now
                session["_hid"]              = hid
                session["_hid_ts"]           = now
                session["_sv"]               = get_session_ver(user_id)
                return redirect(url_for("games.games"))
            log_attempt(email, ip, success=False)
            error = "Correo o contraseña incorrectos"

    return render_template("login.html", error=error, success=success,
                           email=email, page="")


@bp.route("/register", methods=["GET", "POST"])
@limiter.limit("10/hour")
def register():
    if session.get("user_id"):
        return redirect(url_for("games.games"))

    error = None
    email = ""

    if request.method == "POST":
        from werkzeug.security import generate_password_hash

        email     = request.form.get("email", "").strip().lower()
        password  = request.form.get("password", "")
        password2 = request.form.get("password2", "")
        captcha_i = request.form.get("captcha", "")

        if not is_valid_email(email):
            error = "Correo electrónico inválido"

        if not error:
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
                return redirect(url_for("auth.verify_email"))

    captcha_q, captcha_a = new_captcha()
    session["captcha"] = captcha_a
    return render_template("register.html", error=error, email=email,
                           captcha_q=captcha_q, page="")


@bp.route("/verify-email", methods=["GET", "POST"])
def verify_email():
    email = session.get("reg_pending", "")
    if not email:
        return redirect(url_for("auth.register"))

    error   = None
    success = None

    if request.method == "POST":
        code = "".join(request.form.get("code", "").split())
        ok, result = verify_email_code(email, code)
        if ok:
            session.clear()
            session["user_id"]           = result
            session["user_email"]        = email
            session["user_display_name"] = None
            session["user_avatar"]       = None
            return redirect(url_for("games.games"))
        error = result

    return render_template(
        "verify_email.html",
        masked_email=mask_email(email),
        error=error, success=success,
        page="",
    )


@bp.route("/verify-email/resend", methods=["POST"])
def verify_email_resend():
    email = session.get("reg_pending", "")
    if not email:
        return redirect(url_for("auth.register"))

    ok, wait = can_resend(email)
    if not ok:
        return render_template(
            "verify_email.html",
            masked_email=mask_email(email),
            error=f"Espera {wait} segundos antes de reenviar.",
            success=None, page="",
        )

    rec = get_verification(email)
    if not rec:
        return redirect(url_for("auth.register"))

    code = generate_verification_code()
    store_verification(email, rec["pwd_hash"], code)
    sent = send_verification_email(email, code)
    if not sent:
        return render_template(
            "verify_email.html",
            masked_email=mask_email(email),
            error="No pudimos reenviar el correo. Inténtalo más tarde.",
            success=None, page="",
        )

    return render_template(
        "verify_email.html",
        masked_email=mask_email(email),
        error=None, success="Código reenviado. Revisa tu correo.",
        page="",
    )


@bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("games.games"))


# ── Password reset ────────────────────────────────────────────────────────────

@bp.route("/forgot-password")
def forgot_password():
    if session.get("user_id"):
        return redirect(url_for("games.games"))
    return render_template("forgot_password.html", page="")


@bp.route("/api/password-reset/request", methods=["POST"])
@limiter.limit("5/hour")
def api_password_reset_request():
    from flask import jsonify
    data  = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    if not is_valid_email(email):
        return jsonify({"error": "Correo inválido"}), 400

    if not can_resend_reset(email):
        return jsonify({"error": "Espera al menos 60 segundos antes de solicitar otro código"}), 429

    if not mail_is_configured():
        return jsonify({"error": "El servidor de correo no está configurado"}), 503

    code = generate_verification_code()
    store_password_reset(email, code)
    send_password_reset_email(email, code)
    return jsonify({"ok": True})


@bp.route("/api/password-reset/verify", methods=["POST"])
@limiter.limit("10/hour")
def api_password_reset_verify():
    from flask import jsonify
    data  = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    code  = (data.get("code") or "").strip()

    ok, result = verify_password_reset_code(email, code)
    if not ok:
        return jsonify({"error": result}), 400

    token = secrets.token_hex(32)
    session["pr_email"] = email
    session["pr_token"] = token
    delete_password_reset(email)
    return jsonify({"ok": True, "redirect": "/reset-password"})


@bp.route("/reset-password")
def reset_password_page():
    if not session.get("pr_email") or not session.get("pr_token"):
        return redirect(url_for("auth.forgot_password"))
    return render_template("reset_password.html", page="", email=session["pr_email"])


@bp.route("/api/password-reset/confirm", methods=["POST"])
@limiter.limit("10/hour")
def api_password_reset_confirm():
    from flask import jsonify
    if not session.get("pr_email") or not session.get("pr_token"):
        return jsonify({"error": "Sesión de recuperación inválida"}), 403

    data     = request.get_json(silent=True) or {}
    password = data.get("password", "")

    email = session["pr_email"]
    ok, msg = reset_user_password(email, password)
    if not ok:
        return jsonify({"error": msg}), 400

    from_settings = session.pop("pr_from_settings", False)
    session.pop("pr_email", None)
    session.pop("pr_token", None)
    redirect_url = "/settings?pw_changed=1" if from_settings else "/login?reset=1"
    return jsonify({"ok": True, "redirect": redirect_url})
