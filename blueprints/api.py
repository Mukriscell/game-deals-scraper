import time

from flask import Blueprint, jsonify, redirect, render_template, request, send_from_directory, session, url_for

from auth import (
    hide_deal,
    wishlist_get, wishlist_names, wishlist_remove, wishlist_toggle, wishlist_set_alert,
    collection_toggle,
)
from cache import (
    _cache, _search_cache, _aux_cache_lock,
    _SEARCH_CACHE_TTL, _SEARCH_CACHE_MAX,
    _prune_cache, get_data, sidebar_stats,
)
from extensions import limiter

bp = Blueprint('api', __name__)


@bp.route('/health')
def health():
    return jsonify({'status': 'ok'}), 200


@bp.route('/robots.txt')
def robots():
    return send_from_directory('static', 'robots.txt')


@bp.route("/api/search")
@limiter.limit("60/minute")
def api_search():
    from scraper import SESSION, RAWG_API, RAWG_KEY
    q = request.args.get("q", "").strip()
    if len(q) < 2:
        return jsonify([])

    q_key  = q.lower()
    cached = _search_cache.get(q_key)
    if cached and time.time() - cached["ts"] < _SEARCH_CACHE_TTL:
        return jsonify(cached["data"])

    seen  = set()
    local = []
    for d in _cache.get("deals", []):
        if q_key in d["name"].lower():
            local.append({
                "name":     d["name"],
                "type":     "deal",
                "store":    d.get("store", ""),
                "price":    d.get("price", 0),
                "discount": d.get("discount", 0),
                "currency": d.get("currency", "USD"),
                "thumb":    d.get("thumb", ""),
            })
            seen.add(d["name"].lower())
            if len(local) >= 5:
                break

    rawg = []
    if RAWG_KEY:
        try:
            resp = SESSION.get(
                f"{RAWG_API}/games",
                params={"key": RAWG_KEY, "search": q, "page_size": 7, "search_precise": "true"},
                timeout=8,
            )
            if resp.ok:
                for g in (resp.json().get("results") or []):
                    name = g.get("name", "")
                    if name and name.lower() not in seen:
                        rawg.append({"name": name, "type": "rawg", "thumb": g.get("background_image") or ""})
                        seen.add(name.lower())
                        if len(rawg) >= 5:
                            break
        except Exception:
            pass

    results = local + rawg
    with _aux_cache_lock:
        _search_cache[q_key] = {"data": results, "ts": time.time()}
        if len(_search_cache) > _SEARCH_CACHE_MAX:
            _prune_cache(_search_cache, _SEARCH_CACHE_MAX, _SEARCH_CACHE_TTL)
    return jsonify(results)


@bp.route("/api/log/search", methods=["POST"])
@limiter.limit("60/minute")
def api_log_search():
    from admin_db import log_search
    data = request.get_json(silent=True) or {}
    log_search(data.get("query", ""))
    return "", 204


@bp.route("/api/log/click", methods=["POST"])
@limiter.limit("60/minute")
def api_log_click():
    from admin_db import log_click
    data = request.get_json(silent=True) or {}
    log_click(data.get("name", ""), data.get("store", ""))
    return "", 204


# ── Wishlist & hidden deals ───────────────────────────────────────────────────

@bp.route('/api/wishlist/toggle', methods=['POST'])
def api_wishlist_toggle():
    uid = session.get('user_id')
    if not uid:
        return {'error': 'Debes iniciar sesión'}, 401
    data = request.get_json(silent=True) or {}
    in_wl = wishlist_toggle(uid, data)
    session.pop('_wl_ts', None)
    return {'in_wishlist': in_wl}


@bp.route('/api/wishlist/alert', methods=['POST'])
def api_wishlist_alert():
    uid = session.get('user_id')
    if not uid:
        return {'error': 'Debes iniciar sesión'}, 401
    data  = request.get_json(silent=True) or {}
    name  = (data.get('name') or '').strip()
    price = data.get('price')
    if not name:
        return {'error': 'Nombre inválido'}, 400
    if price is not None:
        try:
            price = float(price)
            if price < 0:
                return {'error': 'Precio inválido'}, 400
        except (ValueError, TypeError):
            return {'error': 'Precio inválido'}, 400
    wishlist_set_alert(uid, name, price)
    session.pop('_wl_ts', None)
    return {'ok': True, 'price_alert': price}


@bp.route('/api/collection/toggle', methods=['POST'])
def api_collection_toggle():
    uid = session.get('user_id')
    if not uid:
        return {'error': 'Debes iniciar sesión'}, 401
    data = request.get_json(silent=True) or {}
    name = (data.get('name') or '').strip()
    if not name:
        return {'error': 'Nombre inválido'}, 400
    in_col = collection_toggle(uid, name)
    session.pop('_wl_ts', None)  # force full refresh of all user deal data
    return {'in_collection': in_col}


@bp.route('/api/deals/hide', methods=['POST'])
def api_deal_hide():
    uid = session.get('user_id')
    if not uid:
        return '', 401
    data = request.get_json(silent=True) or {}
    name = (data.get('name') or '').strip()
    if name:
        hide_deal(uid, name)
    session.pop('_hid_ts', None)
    return '', 204


@bp.route('/wishlist')
def user_wishlist():
    uid = session.get('user_id')
    if not uid:
        return redirect(url_for('auth.login'))
    items = wishlist_get(uid)
    deals, _, subscriptions = get_data()
    sb = sidebar_stats(deals, subscriptions)
    return render_template('wishlist.html', items=items, stats=sb, page='wishlist')


@bp.route('/wishlist/remove', methods=['POST'])
def user_wishlist_remove():
    uid = session.get('user_id')
    if not uid:
        return redirect(url_for('auth.login'))
    name = (request.form.get('name') or '').strip()
    if name:
        wishlist_remove(uid, name)
    return redirect(url_for('api.user_wishlist'))
