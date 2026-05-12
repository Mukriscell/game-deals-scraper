import json
import time
from concurrent.futures import ThreadPoolExecutor
from flask import Flask, render_template
from scraper import (
    scrape_deals, scrape_popular, scrape_subscriptions,
    scrape_steamspy_deals, scrape_ggdeals_deals,
    STREAMING_SERVICES, LEARNING_SERVICES,
)

app = Flask(__name__)

_cache = {"deals": [], "featured": [], "subscriptions": [], "ts": 0}
CACHE_TTL = 300


def get_data():
    if time.time() - _cache["ts"] < CACHE_TTL and _cache["deals"]:
        return _cache["deals"], _cache["featured"], _cache["subscriptions"]

    # Fetch all sources in parallel
    with ThreadPoolExecutor(max_workers=4) as pool:
        f_deals    = pool.submit(scrape_deals, 5)
        f_popular  = pool.submit(scrape_popular, 12)
        f_steamspy = pool.submit(scrape_steamspy_deals)
        f_ggdeals  = pool.submit(scrape_ggdeals_deals)
        deals    = f_deals.result()
        popular  = f_popular.result()
        ss_deals = f_steamspy.result()
        gg_deals = f_ggdeals.result()

    # Enrich popular carousel banners with real ITAD thumbnails
    deal_banner = {d["id"]: d["thumb"] for d in deals if d.get("id") and d.get("thumb")}
    for game in popular:
        if game["id"] in deal_banner:
            game["banner"] = deal_banner[game["id"]]

    # Normalize SteamSpy store_id to match whatever ITAD uses for "Steam"
    # so the store filter dropdown doesn't show two "Steam" entries
    itad_steam_id = next(
        (d["store_id"] for d in deals if d["store"] == "Steam"), "steam"
    )
    for d in ss_deals:
        d["store_id"] = itad_steam_id

    # Merge SteamSpy + GG.deals: only add games not already in ITAD results
    seen_names = {d["name"].strip().lower() for d in deals}
    added_ss = added_gg = 0
    for d in ss_deals:
        key = d["name"].strip().lower()
        if key not in seen_names:
            deals.append(d)
            seen_names.add(key)
            added_ss += 1
    for d in gg_deals:
        key = d["name"].strip().lower()
        if key not in seen_names:
            deals.append(d)
            seen_names.add(key)
            added_gg += 1
    print(f"[merge] +{added_ss} SteamSpy +{added_gg} GG.deals (total: {len(deals)})")

    featured = popular

    # Only ITAD game IDs are valid for the subscriptions endpoint
    deal_ids = list({
        d["id"] for d in deals
        if d.get("id") and not d["id"].startswith(("steamspy_", "ggdeals_"))
    })
    sub_map  = scrape_subscriptions(deal_ids) if deal_ids else {}

    subscriptions = [
        {
            "id":       d["id"],
            "title":    d["name"],
            "banner":   d["thumb"],
            "itad_url": d["url"],
            "subs":     sub_map[d["id"]],
        }
        for d in deals
        if d.get("id") and d["id"] in sub_map
    ]

    _cache["deals"]         = deals
    _cache["featured"]      = featured
    _cache["subscriptions"] = subscriptions
    _cache["ts"]            = time.time()

    return deals, featured, subscriptions


def sidebar_stats(deals, subscriptions):
    return {
        "games":      sum(1 for d in deals if d["category"] == "game"),
        "licenses":   len(LEARNING_SERVICES),
        "total_subs": len(STREAMING_SERVICES) + len(subscriptions),
    }


@app.route("/")
@app.route("/games")
def games():
    deals, featured, subscriptions = get_data()
    sb = sidebar_stats(deals, subscriptions)

    game_deals = [d for d in deals if d["category"] == "game"]

    # Ensure carousel (featured) games are searchable even if they didn't
    # make ITAD's top-300-by-discount list (popular ≠ biggest discount).
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
            "id":             g["id"],
            "name":           g["title"],
            "price":          g["price"],
            "original_price": orig,
            "discount":       g["cut"],
            "store":          store_name,
            "store_id":       store_name_to_id.get(store_name, store_name or "itad"),
            "url":            g["url"],
            "thumb":          g.get("banner") or "",
            "metacritic":     0,
            "steam_rating":   0,
            "store_low":      0.0,
            "history_low":    0.0,
            "flag":           None,
            "expiry":         None,
            "voucher":        None,
            "currency":       g.get("currency") or "USD",
            "category":       "game",
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
        featured=featured,
        stores=stores,
        stats=stats,
        page="game",
    )


@app.route("/licencias")
def licencias():
    deals, _, subscriptions = get_data()
    sb = sidebar_stats(deals, subscriptions)

    cat_order = ["courses", "ebooks", "software"]
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
        cat_map=cat_map,
        cat_order=cat_order,
        cat_labels=cat_labels,
        stats={**sb, "total": len(LEARNING_SERVICES)},
        page="license",
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
        stats={**sb, "total": sb["total_subs"]},
        page="subscription",
    )


if __name__ == "__main__":
    app.run(debug=True)
