import json
import time

from flask import Blueprint, jsonify, redirect, render_template, url_for

from cache import (
    _cache, _rawg_detail_cache, _price_hist_cache, _itad_id_cache,
    _aux_cache_lock,
    _RAWG_CACHE_TTL, _RAWG_CACHE_MAX, _PRICE_HIST_TTL, _PRICE_HIST_MAX,
    get_data, sidebar_stats, resolve_itad_id, get_rawg_id,
    section_cached, _prune_cache, _prune_rawg_cache, get_bundles,
)
from affiliates import tag_url
from extensions import limiter
from scraper import (
    fetch_rawg_game_detail, fetch_price_history,
    fetch_game_offers, fetch_game_dlcs, fetch_game_articles,
    fetch_game_streams, fetch_game_similar,
    STREAMING_SERVICES, LEARNING_SERVICES,
)

bp = Blueprint('games', __name__)


@bp.route("/")
@bp.route("/games")
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

    for d in game_deals:
        d["url"] = tag_url(d["url"])

    return render_template(
        "index.html",
        deals_json=json.dumps(game_deals, ensure_ascii=False),
        featured=featured, stores=stores, stats=stats, page="game",
        rawg_popular=rawg_popular,
    )


@bp.route("/game/<path:name>")
def game_detail(name):
    name = name.strip()
    key  = name.lower()

    cached = _rawg_detail_cache.get(key)
    if cached and time.time() - cached["ts"] < _RAWG_CACHE_TTL:
        game_data = cached["data"]
    else:
        game_data = fetch_rawg_game_detail(name)
        with _aux_cache_lock:
            _rawg_detail_cache[key] = {"data": game_data, "ts": time.time()}
            if len(_rawg_detail_cache) > _RAWG_CACHE_MAX:
                _prune_rawg_cache()

    if not game_data:
        deal = next((d for d in _cache.get("deals", [])
                     if d["name"].strip().lower() == key), None)
        return redirect(tag_url(deal["url"]) if deal else url_for("games.games"))

    deal = next((d for d in _cache.get("deals", [])
                 if d["name"].strip().lower() == key), None)
    if deal:
        deal = {**deal, "url": tag_url(deal["url"])}
    return render_template("game_detail.html", game=game_data, deal=deal, page="game")


@bp.route("/licencias")
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


@bp.route("/bundles")
def bundles():
    deals, _, subscriptions = get_data()
    sb = sidebar_stats(deals, subscriptions)
    bundle_list = get_bundles()
    return render_template(
        "bundles.html",
        bundles=bundle_list,
        stats={**sb, "total": len(bundle_list)},
        page="bundle",
    )


@bp.route("/suscripciones")
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


# ── Game section APIs ─────────────────────────────────────────────────────────

@bp.route("/api/game/<path:name>/price-history")
def api_game_price_history(name):
    name    = name.strip()
    itad_id = resolve_itad_id(name)
    if not itad_id:
        return jsonify({"error": "Juego no encontrado en ITAD"}), 404

    cached = _price_hist_cache.get(itad_id)
    if cached and time.time() - cached["ts"] < _PRICE_HIST_TTL:
        if cached["data"] is None:
            return jsonify({"error": "Sin historial disponible"}), 404
        return jsonify(cached["data"])

    data = fetch_price_history(itad_id)
    with _aux_cache_lock:
        _price_hist_cache[itad_id] = {"data": data, "ts": time.time()}
        if len(_price_hist_cache) > _PRICE_HIST_MAX:
            _prune_cache(_price_hist_cache, _PRICE_HIST_MAX, _PRICE_HIST_TTL)

    if not data:
        return jsonify({"error": "Sin historial disponible"}), 404
    return jsonify(data)


@bp.route("/api/game/<path:name>/offers")
@limiter.limit("60/minute")
def api_game_offers(name):
    name    = name.strip()
    itad_id = resolve_itad_id(name)
    if not itad_id:
        return jsonify([])
    data = section_cached(name, "offers", lambda: fetch_game_offers(itad_id))
    return jsonify([{**o, "url": tag_url(o["url"])} for o in data])


@bp.route("/api/game/<path:name>/dlcs")
@limiter.limit("60/minute")
def api_game_dlcs(name):
    name    = name.strip()
    rawg_id = get_rawg_id(name)
    if not rawg_id:
        return jsonify([])
    data = section_cached(name, "dlcs", lambda: fetch_game_dlcs(rawg_id))
    return jsonify(data)


@bp.route("/api/game/<path:name>/articles")
@limiter.limit("60/minute")
def api_game_articles(name):
    name    = name.strip()
    rawg_id = get_rawg_id(name)
    if not rawg_id:
        return jsonify([])
    data = section_cached(name, "articles", lambda: fetch_game_articles(rawg_id))
    return jsonify(data)


@bp.route("/api/game/<path:name>/streams")
@limiter.limit("60/minute")
def api_game_streams(name):
    name    = name.strip()
    rawg_id = get_rawg_id(name)
    if not rawg_id:
        return jsonify([])
    data = section_cached(name, "streams", lambda: fetch_game_streams(rawg_id))
    return jsonify(data)


@bp.route("/api/game/<path:name>/similar")
@limiter.limit("60/minute")
def api_game_similar(name):
    name    = name.strip()
    rawg_id = get_rawg_id(name)
    if not rawg_id:
        return jsonify([])
    data = section_cached(name, "similar", lambda: fetch_game_similar(rawg_id))
    return jsonify(data)
