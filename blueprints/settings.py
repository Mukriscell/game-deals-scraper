import base64
import datetime
import hmac
import os
import pathlib
import re
import secrets

from flask import Blueprint, jsonify, redirect, render_template, request, session, url_for

from auth import (
    collection_bulk_insert,
    confirm_email_change, delete_user, email_exists, generate_verification_code,
    get_session_ver, get_user_profile, request_email_change, rotate_session_ver,
    update_newsletter_pref, update_user_avatar, update_user_profile,
)
from extensions import csrf, limiter
from mail import (
    is_configured as mail_is_configured,
    send_account_deletion_email,
    send_verification_email,
)
from utils import is_valid_email, mask_email

bp = Blueprint('settings', __name__)

_AVATAR_DIR      = pathlib.Path(__file__).parent.parent / "static" / "uploads" / "avatars"
_USER_UPLOAD_RE  = re.compile(r'^\d+_[0-9a-f]{16}\.(png|jpg|jpeg)$')
_IGNORED_PRESETS = {'2_0cfa4863c6d35c56.jpg'}


def _get_preset_avatars() -> list[str]:
    if not _AVATAR_DIR.exists():
        return []
    return sorted(
        f.name for f in _AVATAR_DIR.iterdir()
        if f.is_file()
        and f.name not in _IGNORED_PRESETS
        and not _USER_UPLOAD_RE.match(f.name)
    )


@bp.route("/settings")
def settings_page():
    if not session.get("user_id"):
        return redirect(url_for("auth.login"))
    profile = get_user_profile(session["user_id"])
    from cache import _cache, sidebar_stats
    from scraper import STREAMING_SERVICES
    sb = sidebar_stats(_cache.get("deals", []), _cache.get("subscriptions", []))
    return render_template(
        "settings.html", profile=profile, stats=sb,
        preset_avatars=_get_preset_avatars(), page="",
    )


@bp.route("/settings/change-password")
def settings_change_password():
    if not session.get("user_id"):
        return redirect(url_for("auth.login"))
    session["pr_email"]         = session["user_email"]
    session["pr_token"]         = secrets.token_hex(32)
    session["pr_from_settings"] = True
    return redirect(url_for("auth.reset_password_page"))


# ── Avatar upload ─────────────────────────────────────────────────────────────

@bp.route('/api/settings/avatar', methods=['POST'])
@limiter.limit("10/hour")
def api_settings_avatar():
    uid = session.get('user_id')
    if not uid:
        return jsonify({'error': 'No autenticado'}), 401

    try:
        body = request.get_json(silent=True) or {}
        b64  = body.get('data', '')
        if not b64:
            return jsonify({'error': 'No se envio imagen'}), 400

        try:
            content = base64.b64decode(b64)
        except Exception:
            return jsonify({'error': 'Datos de imagen invalidos'}), 400

        if len(content) > 2 * 1024 * 1024:
            return jsonify({'error': 'La imagen no puede superar 2 MB'}), 400

        if content[:4] == b'\x89PNG':
            ext = 'png'
        elif content[:3] == b'\xff\xd8\xff':
            ext = 'jpg'
        else:
            return jsonify({'error': 'Solo se aceptan imagenes PNG o JPG'}), 400

        _AVATAR_DIR.mkdir(parents=True, exist_ok=True)

        profile = get_user_profile(uid)
        if profile and profile.get('avatar'):
            old_name = profile['avatar']
            if _USER_UPLOAD_RE.match(old_name):
                try:
                    (_AVATAR_DIR / old_name).unlink(missing_ok=True)
                except Exception:
                    pass

        filename = f"{uid}_{secrets.token_hex(8)}.{ext}"
        (_AVATAR_DIR / filename).write_bytes(content)

        update_user_avatar(uid, filename)
        session['user_avatar'] = filename
        return jsonify({'avatar_url': f'/static/uploads/avatars/{filename}'})

    except Exception:
        return jsonify({'error': 'Error al guardar la imagen. Inténtalo de nuevo.'}), 500


@bp.route('/api/settings/avatar/preset', methods=['POST'])
@limiter.limit("20/hour")
def api_settings_avatar_preset():
    uid = session.get('user_id')
    if not uid:
        return jsonify({'error': 'No autenticado'}), 401

    data     = request.get_json(silent=True) or {}
    filename = (data.get('filename') or '').strip()

    allowed = _get_preset_avatars()
    if filename not in allowed:
        return jsonify({'error': 'Avatar no válido'}), 400

    profile = get_user_profile(uid)
    if profile and profile.get('avatar'):
        old_name = profile['avatar']
        if _USER_UPLOAD_RE.match(old_name):
            try:
                (_AVATAR_DIR / old_name).unlink(missing_ok=True)
            except Exception:
                pass

    update_user_avatar(uid, filename)
    session['user_avatar'] = filename
    return jsonify({'avatar_url': f'/static/uploads/avatars/{filename}'})


# ── Profile & email ───────────────────────────────────────────────────────────

@bp.route('/api/settings/profile', methods=['POST'])
def api_settings_profile():
    uid = session.get('user_id')
    if not uid:
        return {'error': 'No autenticado'}, 401

    data         = request.get_json(silent=True) or {}
    display_name = (data.get('display_name') or '').strip()[:100]
    phone        = (data.get('phone') or '').strip()[:30]
    email_notif  = 1 if data.get('email_notifications') else 0

    update_user_profile(uid, display_name or None, phone or None, email_notif)
    session['user_display_name'] = display_name or None
    return {'ok': True}


@bp.route('/api/settings/email/request', methods=['POST'])
@limiter.limit("5/hour")
def api_settings_email_request():
    uid = session.get('user_id')
    if not uid:
        return {'error': 'No autenticado'}, 401

    data      = request.get_json(silent=True) or {}
    new_email = (data.get('email') or '').strip().lower()

    if not is_valid_email(new_email):
        return {'error': 'Correo inválido'}, 400
    if new_email == session.get('user_email', ''):
        return {'error': 'Es el mismo correo actual'}, 400
    if email_exists(new_email):
        return {'error': 'Este correo ya esta registrado'}, 400
    if not mail_is_configured():
        return {'error': 'El servicio de correo no esta configurado'}, 503

    code = generate_verification_code()
    request_email_change(uid, new_email, code)
    sent = send_verification_email(new_email, code)
    if not sent:
        return {'error': 'No se pudo enviar el correo de verificacion'}, 503

    return {'ok': True, 'masked': mask_email(new_email)}


@bp.route('/api/settings/email/confirm', methods=['POST'])
@limiter.limit("10/hour")
def api_settings_email_confirm():
    uid = session.get('user_id')
    if not uid:
        return {'error': 'No autenticado'}, 401

    data = request.get_json(silent=True) or {}
    code = (data.get('code') or '').strip()
    ok, result = confirm_email_change(uid, code)
    if ok:
        session['user_email'] = result
        return {'ok': True, 'new_email': result}
    return {'error': result}, 400


# ── Account deletion ──────────────────────────────────────────────────────────

@bp.route('/api/settings/delete-account/request', methods=['POST'])
@limiter.limit("5/hour")
def api_delete_account_request():
    uid = session.get('user_id')
    if not uid:
        return {'error': 'No autenticado'}, 401
    if not mail_is_configured():
        return {'error': 'El servicio de correo no está configurado'}, 503

    code = generate_verification_code()
    session['del_code'] = code
    session['del_exp']  = (
        datetime.datetime.utcnow() + datetime.timedelta(minutes=15)
    ).isoformat()

    sent = send_account_deletion_email(session['user_email'], code)
    if not sent:
        return {'error': 'No se pudo enviar el correo de confirmación'}, 503

    return {'ok': True, 'masked': mask_email(session['user_email'])}


@bp.route('/api/settings/delete-account/confirm', methods=['POST'])
@limiter.limit("10/hour")
def api_delete_account_confirm():
    uid = session.get('user_id')
    if not uid:
        return {'error': 'No autenticado'}, 401

    data = request.get_json(silent=True) or {}
    code = (data.get('code') or '').strip()

    stored_code = session.get('del_code', '')
    stored_exp  = session.get('del_exp', '')

    if not stored_code or not stored_exp:
        return {'error': 'No hay solicitud de eliminación pendiente'}, 400

    try:
        exp_dt = datetime.datetime.fromisoformat(stored_exp)
    except ValueError:
        return {'error': 'Solicitud inválida'}, 400

    if datetime.datetime.utcnow() > exp_dt:
        session.pop('del_code', None)
        session.pop('del_exp', None)
        return {'error': 'El código ha expirado. Solicita uno nuevo.'}, 400

    if not hmac.compare_digest(code, stored_code):
        return {'error': 'Código incorrecto'}, 400

    email = session.get('user_email', '')
    delete_user(uid, email)
    session.clear()
    return {'ok': True}


# ── Newsletter preference ─────────────────────────────────────────────────────

@bp.route('/api/settings/newsletter', methods=['POST'])
def api_settings_newsletter():
    uid = session.get('user_id')
    if not uid:
        return {'error': 'No autenticado'}, 401
    data    = request.get_json(silent=True) or {}
    enabled = bool(data.get('enabled'))
    update_newsletter_pref(uid, enabled)
    return {'ok': True, 'newsletter': enabled}


# ── Steam library import ──────────────────────────────────────────────────────

@bp.route('/api/settings/steam-import', methods=['POST'])
@limiter.limit("5/hour")
def api_steam_import():
    uid = session.get('user_id')
    if not uid:
        return {'error': 'No autenticado'}, 401

    steam_key = os.environ.get('STEAM_API_KEY', '')
    if not steam_key:
        return {'error': 'La integración con Steam no está configurada'}, 503

    data     = request.get_json(silent=True) or {}
    steam_id = (data.get('steam_id') or '').strip()
    if not steam_id:
        return {'error': 'Introduce tu Steam ID'}, 400

    # Resolve vanity URL to SteamID64
    if not steam_id.isdigit():
        try:
            import requests as _req
            resp = _req.get(
                'https://api.steampowered.com/ISteamUser/ResolveVanityURL/v0001/',
                params={'key': steam_key, 'vanityurl': steam_id},
                timeout=8,
            )
            r = resp.json().get('response', {})
            if r.get('success') != 1:
                return {'error': 'No se encontró ese perfil de Steam'}, 404
            steam_id = r['steamid']
        except Exception:
            return {'error': 'Error al contactar la API de Steam'}, 502

    try:
        import requests as _req
        resp = _req.get(
            'https://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/',
            params={
                'key':             steam_key,
                'steamid':         steam_id,
                'include_appinfo': 1,
                'format':          'json',
            },
            timeout=12,
        )
        games = resp.json().get('response', {}).get('games') or []
    except Exception:
        return {'error': 'Error al obtener la biblioteca de Steam'}, 502

    if not games:
        return {'error': 'La biblioteca está vacía o es privada'}, 404

    names = [g['name'] for g in games if g.get('name')]
    added = collection_bulk_insert(uid, names)
    session.pop('_wl_ts', None)
    return {'ok': True, 'total': len(names), 'added': added}


# ── Session management ────────────────────────────────────────────────────────

@bp.route('/api/settings/sessions/revoke', methods=['POST'])
@limiter.limit("10/hour")
def api_sessions_revoke():
    uid = session.get('user_id')
    if not uid:
        return {'error': 'No autenticado'}, 401

    new_ver = rotate_session_ver(uid)
    session['_sv'] = new_ver
    return {'ok': True}
