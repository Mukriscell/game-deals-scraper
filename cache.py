import json
import pathlib
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor

from scraper import (
    scrape_deals, scrape_popular, scrape_rawg_popular,
    scrape_subscriptions, scrape_steamspy_deals, scrape_ggdeals_deals,
    scrape_bundles,
    fetch_game_offers, fetch_game_dlcs, fetch_game_articles,
    fetch_game_streams, fetch_game_similar,
    lookup_itad_id, fetch_price_history,
    STREAMING_SERVICES, LEARNING_SERVICES,
)

# ── In-memory caches ──────────────────────────────────────────────────────────

_cache: dict = {
    "deals": [], "featured": [], "subscriptions": [], "rawg": [],
    "bundles": [], "bundles_ts": 0,
    "ts": 0, "refreshing": False,
}
_BUNDLE_TTL = 3600
_cache_lock     = threading.Lock()
_aux_cache_lock = threading.Lock()

_rawg_detail_cache: dict = {}   # {name_lower: {"data": dict|None, "ts": float}}
_price_hist_cache:  dict = {}   # {itad_id:   {"data": dict|None, "ts": float}}
_itad_id_cache:     dict = {}   # {name_lower: {"id": str|None,  "ts": float}}
_game_section_cache: dict = {}  # {f"{name}:{section}": {"data": list, "ts": float}}
_search_cache:       dict = {}  # {q_lower: {"data": list, "ts": float}}

_RAWG_CACHE_TTL    = 3600
_RAWG_CACHE_MAX    = 200
_PRICE_HIST_TTL    = 21600
_PRICE_HIST_MAX    = 500
_ITAD_ID_TTL       = 86400
_ITAD_ID_MAX       = 500
_SECTION_CACHE_TTL = 3600
_SECTION_CACHE_MAX = 1000
_SEARCH_CACHE_TTL  = 120
_SEARCH_CACHE_MAX  = 200
CACHE_TTL_DEFAULT  = 300

_CACHE_FILE = pathlib.Path(__file__).parent / "cache_data.json"
_db_ready   = threading.Event()


# ── Persistence ───────────────────────────────────────────────────────────────

def _save_cache():
    try:
        with open(_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(
                {k: _cache[k] for k in ('deals', 'featured', 'subscriptions', 'rawg', 'ts')},
                f, ensure_ascii=False, default=str,
            )
    except Exception:
        pass


def _load_cache():
    try:
        if not _CACHE_FILE.exists():
            return
        with open(_CACHE_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        _cache.update({
            'deals':         data.get('deals', []),
            'featured':      data.get('featured', []),
            'subscriptions': data.get('subscriptions', []),
            'rawg':          data.get('rawg', []),
            'ts':            data.get('ts', 0),
        })
    except Exception:
        pass


# ── Refresh ───────────────────────────────────────────────────────────────────

def _do_refresh():
    from admin_db import get_config, log_cache_refresh, is_blacklisted, log_error

    t0 = time.time()
    source_counts = {'ITAD': 0, 'SteamSpy': 0, 'GG.deals': 0}
    error_msg     = ''
    use_ss = get_config('source_steamspy', '1') == '1'
    use_gg = get_config('source_ggdeals', '1') == '1'

    try:
        with ThreadPoolExecutor(max_workers=5) as pool:
            f_deals   = pool.submit(scrape_deals, 15)
            f_popular = pool.submit(scrape_popular, 20)
            f_rawg    = pool.submit(scrape_rawg_popular, 40)
            f_ss      = pool.submit(scrape_steamspy_deals) if use_ss else None
            f_gg      = pool.submit(scrape_ggdeals_deals)  if use_gg else None
            deals     = f_deals.result()
            popular   = f_popular.result()
            rawg_list = f_rawg.result()
            ss_result = f_ss.result() if f_ss else ([], {})
            ss_deals, ss_pop = ss_result if isinstance(ss_result, tuple) else (ss_result, {})
            gg_deals  = f_gg.result() if f_gg else []
        source_counts['ITAD'] = len(deals)
    except Exception as exc:
        log_error('get_data', type(exc).__name__, str(exc), traceback.format_exc())
        error_msg = str(exc)
        deals = popular = ss_deals = gg_deals = rawg_list = []
        ss_pop = {}

    deal_banner = {d["id"]: d["thumb"] for d in deals if d.get("id") and d.get("thumb")}
    for game in popular:
        if game["id"] in deal_banner:
            game["banner"] = deal_banner[game["id"]]

    itad_steam_id = next((d["store_id"] for d in deals if d["store"] == "Steam"), "steam")
    for d in ss_deals:
        d["store_id"] = itad_steam_id

    seen = {d["name"].strip().lower() for d in deals}
    for d in ss_deals:
        key = d["name"].strip().lower()
        if key not in seen:
            deals.append(d); seen.add(key); source_counts['SteamSpy'] += 1
    for d in gg_deals:
        key = d["name"].strip().lower()
        if key not in seen:
            deals.append(d); seen.add(key); source_counts['GG.deals'] += 1

    print(f"[merge] ITAD:{source_counts['ITAD']} "
          f"+SS:{source_counts['SteamSpy']} +GG:{source_counts['GG.deals']} "
          f"(total: {len(deals)})")

    combined_pop = {d['name'].strip().lower(): d.get('popularity', 0)
                    for d in gg_deals + ss_deals if d.get('popularity', 0) > 0}
    combined_pop.update(ss_pop)
    for d in deals:
        if not d.get('popularity'):
            d['popularity'] = combined_pop.get(d['name'].strip().lower(), 0)

    deals = [d for d in deals if not is_blacklisted(d['name'])]

    carousel_pin = get_config('carousel_pin', '').strip()
    if carousel_pin:
        pin_l  = carousel_pin.lower()
        pinned = next((d for d in deals if d['name'].strip().lower() == pin_l), None)
        if pinned:
            pf = {
                'id': pinned.get('id', ''), 'title': pinned['name'],
                'price': pinned['price'], 'banner': pinned.get('thumb', ''),
                'url': pinned['url'], 'store': pinned.get('store', ''),
                'cut': pinned['discount'], 'on_sale': True,
                'currency': pinned.get('currency', 'USD'),
            }
            popular = [f for f in popular if f.get('title', '').strip().lower() != pin_l]
            popular = [pf] + popular[:11]

    featured = popular
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

    with _cache_lock:
        _cache.update({
            "deals": deals, "featured": featured,
            "subscriptions": subscriptions, "rawg": rawg_list,
            "ts": time.time(), "refreshing": False,
        })
    _save_cache()

    duration_ms = int((time.time() - t0) * 1000)
    log_cache_refresh(len(deals), duration_ms, json.dumps(source_counts), error_msg)


def get_data():
    from admin_db import get_config
    cache_ttl = int(get_config('cache_ttl', str(CACHE_TTL_DEFAULT)))
    age = time.time() - _cache["ts"]

    if age < cache_ttl and _cache["deals"]:
        return _cache["deals"], _cache["featured"], _cache["subscriptions"]

    if _CACHE_FILE.exists():
        try:
            if time.time() - _CACHE_FILE.stat().st_mtime < cache_ttl:
                _load_cache()
                if _cache["deals"]:
                    return _cache["deals"], _cache["featured"], _cache["subscriptions"]
        except OSError:
            pass

    if _cache["deals"]:
        with _cache_lock:
            if not _cache["refreshing"]:
                _cache["refreshing"] = True
                threading.Thread(target=_do_refresh, daemon=True).start()
        return _cache["deals"], _cache["featured"], _cache["subscriptions"]

    deadline = time.time() + 45
    while not _cache["deals"] and time.time() < deadline:
        time.sleep(0.5)

    return _cache["deals"], _cache["featured"], _cache["subscriptions"]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _prune_cache(d: dict, max_size: int, ttl: float):
    """Evict expired entries then trim to max_size by age. Must be called under _aux_cache_lock."""
    now = time.time()
    for k in [k for k, v in d.items() if now - v["ts"] > ttl]:
        d.pop(k, None)
    if len(d) > max_size:
        oldest = sorted(d, key=lambda k: d[k]["ts"])
        for k in oldest[:len(d) - max_size]:
            d.pop(k, None)


def _prune_rawg_cache():
    _prune_cache(_rawg_detail_cache, _RAWG_CACHE_MAX, _RAWG_CACHE_TTL)


def sidebar_stats(deals, subscriptions):
    return {
        "games":      sum(1 for d in deals if d["category"] == "game"),
        "licenses":   len(LEARNING_SERVICES),
        "total_subs": len(STREAMING_SERVICES) + len(subscriptions),
    }


def resolve_itad_id(name: str):
    key  = name.strip().lower()
    deal = next((d for d in _cache.get("deals", []) if d["name"].strip().lower() == key), None)
    if deal:
        itad_id = deal.get("id", "")
        if itad_id and not itad_id.startswith(("steamspy_", "ggdeals_")):
            return itad_id

    cached = _itad_id_cache.get(key)
    if cached and time.time() - cached["ts"] < _ITAD_ID_TTL:
        return cached["id"]

    itad_id = lookup_itad_id(name.strip())
    with _aux_cache_lock:
        _itad_id_cache[key] = {"id": itad_id, "ts": time.time()}
        if len(_itad_id_cache) > _ITAD_ID_MAX:
            _prune_cache(_itad_id_cache, _ITAD_ID_MAX, _ITAD_ID_TTL)
    return itad_id


def get_rawg_id(name: str):
    cached = _rawg_detail_cache.get(name.strip().lower())
    if cached and cached.get("data"):
        return cached["data"].get("id")
    return None


def section_cached(name: str, section: str, fetcher):
    key    = f"{name}:{section}"
    cached = _game_section_cache.get(key)
    if cached and time.time() - cached["ts"] < _SECTION_CACHE_TTL:
        return cached["data"]
    data = fetcher()
    with _aux_cache_lock:
        _game_section_cache[key] = {"data": data, "ts": time.time()}
        if len(_game_section_cache) > _SECTION_CACHE_MAX:
            _prune_cache(_game_section_cache, _SECTION_CACHE_MAX, _SECTION_CACHE_TTL)
    return data


# ── Background threads ────────────────────────────────────────────────────────

def _check_wishlist_notifications():
    from mail import send_price_change_email, send_price_alert_email, send_expiry_warning_email, is_configured
    from auth import wishlist_get_all_with_emails, wishlist_update_notification
    from datetime import datetime, timezone

    if not is_configured() or not _cache.get("deals"):
        return

    deal_map = {d["name"].strip().lower(): d for d in _cache["deals"]}
    now = time.time()

    try:
        items = wishlist_get_all_with_emails()
    except Exception:
        return

    for item in items:
        deal = deal_map.get(item["deal_name"].strip().lower())
        if not deal:
            continue

        current_price   = float(deal.get("price") or 0)
        currency        = deal.get("currency") or "USD"
        url             = deal.get("url") or ""
        store           = deal.get("store") or ""
        last_price      = item["last_price"]
        notified_expiry = item["notified_expiry"] or 0
        new_last_price  = current_price
        new_notif_exp   = notified_expiry

        price_alert = item.get("price_alert")

        # Price alert: notify when price drops to/below the user's target
        if price_alert is not None and current_price > 0 and current_price <= price_alert:
            if last_price is None or float(last_price) > price_alert:
                try:
                    send_price_alert_email(
                        item["email"], item["deal_name"],
                        float(price_alert), current_price, url, currency, store,
                    )
                except Exception:
                    pass

        # General price change notification
        if last_price is not None and abs(current_price - last_price) > 0.01:
            try:
                send_price_change_email(
                    item["email"], item["deal_name"],
                    float(last_price), current_price, url, currency, store,
                )
            except Exception:
                pass

        expiry = deal.get("expiry")
        if expiry and notified_expiry == 0:
            try:
                exp_dt    = datetime.fromisoformat(str(expiry).replace('Z', '+00:00'))
                days_left = (exp_dt.timestamp() - now) / 86400
                if 0 < days_left <= 2:
                    send_expiry_warning_email(
                        item["email"], item["deal_name"],
                        current_price, str(expiry), url, currency, store,
                        max(1, int(days_left) + (1 if days_left % 1 > 0 else 0)),
                    )
                    new_notif_exp = 1
            except Exception:
                pass
        elif not expiry:
            new_notif_exp = 0

        if new_last_price != last_price or new_notif_exp != notified_expiry:
            try:
                wishlist_update_notification(item["id"], new_last_price, new_notif_exp)
            except Exception:
                pass


def _wishlist_notifier_loop():
    time.sleep(300)
    while True:
        try:
            _check_wishlist_notifications()
        except Exception as exc:
            try:
                from admin_db import log_error
                log_error("wishlist_notifier", str(exc))
            except Exception:
                pass
        time.sleep(3600)


def _db_keepalive_loop():
    from db import get_connection
    while True:
        time.sleep(240)
        try:
            con = get_connection()
            con.cursor().execute("SELECT 1")
            con.close()
        except Exception as exc:
            try:
                from admin_db import log_error
                log_error("db_keepalive", str(exc))
            except Exception:
                pass


def _db_warmup():
    from db import get_connection
    try:
        con = get_connection()
        con.cursor().execute("SELECT 1")
        con.close()
    except Exception:
        pass
    finally:
        _db_ready.set()


def get_bundles() -> list:
    """Return cached bundles, refreshing if stale (1h TTL)."""
    age = time.time() - _cache.get("bundles_ts", 0)
    if age > _BUNDLE_TTL or not _cache.get("bundles"):
        try:
            bundles = scrape_bundles()
        except Exception:
            bundles = []
        with _cache_lock:
            _cache["bundles"]    = bundles
            _cache["bundles_ts"] = time.time()
    return _cache.get("bundles", [])


def _do_newsletter():
    """Send weekly newsletter to all subscribed users."""
    from mail import send_newsletter_email, is_configured
    from auth import get_newsletter_subscribers
    if not is_configured():
        return
    deals = _cache.get("deals", [])
    if not deals:
        return
    top = sorted(
        [d for d in deals if d.get("discount", 0) >= 40 and d.get("category") == "game"],
        key=lambda d: d.get("discount", 0),
        reverse=True,
    )[:10]
    if not top:
        top = sorted(deals, key=lambda d: d.get("discount", 0), reverse=True)[:10]
    subscribers = get_newsletter_subscribers()
    sent = 0
    for sub in subscribers:
        try:
            send_newsletter_email(sub["email"], top)
            sent += 1
        except Exception:
            pass
    print(f"[newsletter] sent to {sent}/{len(subscribers)} subscribers")


def _newsletter_loop():
    """Run newsletter every 7 days, starting after a short delay."""
    time.sleep(600)
    while True:
        try:
            _do_newsletter()
        except Exception as exc:
            try:
                from admin_db import log_error
                log_error("newsletter_loop", type(exc).__name__, str(exc))
            except Exception:
                pass
        time.sleep(7 * 86400)


def start_background_threads():
    _load_cache()
    if not _cache["refreshing"]:
        _cache["refreshing"] = True
        threading.Thread(target=_do_refresh, daemon=True).start()
    threading.Thread(target=_wishlist_notifier_loop, daemon=True).start()
    threading.Thread(target=_db_keepalive_loop, daemon=True).start()
    threading.Thread(target=_db_warmup, daemon=True).start()
    threading.Thread(target=_newsletter_loop, daemon=True).start()
