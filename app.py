import json
import os
import pathlib
import secrets
import time
import traceback

from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from flask_wtf.csrf import CSRFError
from werkzeug.middleware.proxy_fix import ProxyFix

from extensions import csrf, limiter
from cache import _cache, get_data, sidebar_stats, start_background_threads
from auth import (
    get_session_ver, get_all_user_deal_data,
    init_db, init_email_change_table, init_email_verification_table,
    init_password_reset_table, init_wishlist_tables, init_collections_table,
    update_user_last_seen,
)
from admin_db import init_admin_tables

from blueprints.games    import bp as games_bp
from blueprints.auth     import bp as auth_bp
from blueprints.settings import bp as settings_bp
from blueprints.admin    import bp as admin_bp
from blueprints.api      import bp as api_bp


def create_app() -> Flask:
    _missing = [v for v in ("DATABASE_URL", "SECRET_KEY") if not os.environ.get(v)]
    if _missing:
        raise RuntimeError(f"Variables de entorno requeridas no configuradas: {', '.join(_missing)}")

    app = Flask(__name__)
    app.secret_key = os.environ.get("SECRET_KEY")

    # ── Extensions ────────────────────────────────────────────────────────────
    app.config['WTF_CSRF_HEADERS'] = ['X-CSRFToken']
    csrf.init_app(app)
    limiter.init_app(app)

    # ── Session security ──────────────────────────────────────────────────────
    app.config['SESSION_COOKIE_SECURE']   = os.environ.get('FLASK_ENV') == 'production'
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

    # ── Reverse proxy ─────────────────────────────────────────────────────────
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    # ── DB & table init ───────────────────────────────────────────────────────
    init_db()
    init_admin_tables()
    init_wishlist_tables()
    init_collections_table()
    init_email_verification_table()
    init_email_change_table()
    init_password_reset_table()

    # ── Avatar directory ──────────────────────────────────────────────────────
    avatar_dir = pathlib.Path(__file__).parent / "static" / "uploads" / "avatars"
    avatar_dir.mkdir(parents=True, exist_ok=True)

    # ── Blueprints ────────────────────────────────────────────────────────────
    app.register_blueprint(games_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)

    # ── Security headers ──────────────────────────────────────────────────────
    @app.after_request
    def set_security_headers(response):
        response.headers['X-Frame-Options']        = 'SAMEORIGIN'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-XSS-Protection']       = '1; mode=block'
        response.headers['Referrer-Policy']        = 'strict-origin-when-cross-origin'
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self';"
        )
        if os.environ.get('FLASK_ENV') == 'production':
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        return response

    # ── Context processors ────────────────────────────────────────────────────
    @app.context_processor
    def inject_user():
        return {
            "current_user":      session.get("user_email"),
            "user_display_name": session.get("user_display_name"),
            "user_avatar":       session.get("user_avatar"),
        }

    @app.context_processor
    def inject_banner():
        from admin_db import get_config
        active = get_config('banner_active') == '1'
        return {
            'banner_active': active,
            'banner_text':   get_config('banner_text') if active else '',
        }

    @app.context_processor
    def inject_sidebar_stats():
        return {"stats": sidebar_stats(_cache.get("deals", []), _cache.get("subscriptions", []))}

    @app.context_processor
    def inject_user_deal_data():
        uid = session.get('user_id')
        if not uid:
            return {
                'user_wishlist_names':    '[]',
                'user_hidden_names':      '[]',
                'user_collection_names':  '[]',
            }
        now = time.time()
        stale = now - session.get('_wl_ts', 0) > 60
        if stale:
            wl, hid, col = get_all_user_deal_data(uid)
            ts = time.time()
            session['_wl']  = wl;  session['_wl_ts']  = ts
            session['_hid'] = hid; session['_hid_ts'] = ts
            session['_col'] = col; session['_col_ts'] = ts
        return {
            'user_wishlist_names':   json.dumps(session.get('_wl',  [])),
            'user_hidden_names':     json.dumps(session.get('_hid', [])),
            'user_collection_names': json.dumps(session.get('_col', [])),
        }

    # ── Middleware ────────────────────────────────────────────────────────────
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
    def check_session_version():
        uid = session.get('user_id')
        sv  = session.get('_sv')
        if uid and sv is not None and get_session_ver(uid) != sv:
            session.clear()
            return redirect(url_for('auth.login'))

    @app.before_request
    def refresh_last_seen():
        uid = session.get('user_id')
        if uid:
            now = time.time()
            if now - session.get('_ls', 0) > 300:
                session['_ls'] = now
                update_user_last_seen(uid)

    # ── Error handlers ────────────────────────────────────────────────────────
    @app.errorhandler(Exception)
    def handle_exception(e):
        if app.debug:
            raise e
        from admin_db import log_error
        log_error(request.path, type(e).__name__, str(e), traceback.format_exc())
        return render_template('500.html'), 500

    @app.errorhandler(404)
    def handle_404(e):
        return render_template('404.html'), 404

    @app.errorhandler(CSRFError)
    def handle_csrf_error(e):
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Token CSRF inválido. Recarga la página.'}), 400
        return render_template('500.html'), 400

    return app


app = create_app()
start_background_threads()


if __name__ == "__main__":
    import threading
    import webbrowser
    from cache import _db_ready

    debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    port  = int(os.environ.get('PORT', 5000))

    if not debug:
        def _open_browser():
            _db_ready.wait(timeout=8)
            try:
                b = webbrowser.get('firefox')
            except webbrowser.Error:
                b = webbrowser
            b.open(f'http://127.0.0.1:{port}')
        threading.Thread(target=_open_browser, daemon=True).start()

    app.run(debug=debug, port=port)
