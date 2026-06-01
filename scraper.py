import os
import re
import time
from datetime import datetime, timezone
import bleach
import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

ITAD_API     = "https://api.isthereanydeal.com"
ITAD_KEY     = os.environ.get("ITAD_API_KEY", "")
STEAMSPY_API = "https://steamspy.com/api.php"
GGDEALS_API  = "https://api.gg.deals/v1/prices/by-steam-app-id/"
GGDEALS_KEY  = os.environ.get("GGDEALS_API_KEY", "")
RAWG_API     = "https://api.rawg.io/api"
RAWG_KEY     = os.environ.get("RAWG_API_KEY", "")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
}

SESSION = requests.Session()
SESSION.headers.update(HEADERS)

def _safe_url(url: str) -> str:
    """Return url only if it uses http(s); prevents javascript: URI injection."""
    url = (url or "").strip()
    return url if url.startswith(("http://", "https://")) else ""


LICENSE_STORES = {
    "Fanatical", "Humble Store", "Humble Bundle", "GameBillet", "2game",
    "Nuuvem", "DLGamer", "Green Man Gaming", "WinGameStore", "IndieGala Store",
    "Voidu", "Gamesplanet", "AllYouPlay", "Allyouplay", "eTail.Market",
    "MacGameStore", "GamersGate", "Eneba", "Kinguin", "G2A", "GameStop",
    "Amazon", "GameBoom", "GameDeals", "Chrono.gg",
}

LEARNING_SERVICES = [
    # ── Cursos y Certificaciones ───────────────────────
    {
        "id": "udemy", "title": "Udemy", "category": "courses",
        "color": "#A435F0", "text_color": "#ffffff",
        "url": "https://www.udemy.com",
        "description": "Miles de cursos de programación, diseño, marketing y negocios",
        "plans": [
            {"name": "Curso individual", "price": 12.99, "currency": "USD"},
            {"name": "Udemy Business",   "price": 30.00, "currency": "USD"},
        ],
    },
    {
        "id": "coursera", "title": "Coursera", "category": "courses",
        "color": "#0056D2", "text_color": "#ffffff",
        "url": "https://www.coursera.org",
        "description": "Certificaciones y títulos de universidades líderes mundiales",
        "plans": [
            {"name": "Coursera Plus",         "price": 59.00,  "currency": "USD"},
            {"name": "Coursera Plus (anual)",  "price": 399.00, "currency": "USD"},
        ],
    },
    {
        "id": "linkedin_learning", "title": "LinkedIn Learning", "category": "courses",
        "color": "#0A66C2", "text_color": "#ffffff",
        "url": "https://www.linkedin.com/learning",
        "description": "Más de 21,000 cursos impartidos por expertos del sector",
        "plans": [
            {"name": "Individual (mensual)", "price": 39.99, "currency": "USD"},
            {"name": "Individual (anual)",   "price": 19.99, "currency": "USD"},
        ],
    },
    {
        "id": "pluralsight", "title": "Pluralsight", "category": "courses",
        "color": "#F15B2A", "text_color": "#ffffff",
        "url": "https://www.pluralsight.com",
        "description": "Formación técnica: cloud, ciberseguridad, datos e IA",
        "plans": [
            {"name": "Standard", "price": 29.00, "currency": "USD"},
            {"name": "Premium",  "price": 45.00, "currency": "USD"},
        ],
    },
    {
        "id": "edx", "title": "edX", "category": "courses",
        "color": "#02262B", "text_color": "#ffffff",
        "url": "https://www.edx.org",
        "description": "Cursos gratuitos y de pago de MIT, Harvard, Microsoft y más",
        "plans": [
            {"name": "edX Executive Education", "price": 199.00, "currency": "USD"},
        ],
    },
    # ── Libros y Ebooks ───────────────────────────────
    {
        "id": "oreilly", "title": "O'Reilly Learning", "category": "ebooks",
        "color": "#D3002D", "text_color": "#ffffff",
        "url": "https://www.oreilly.com",
        "description": "Libros técnicos, videos y tutoriales de tecnología",
        "plans": [
            {"name": "Individual", "price": 49.00, "currency": "USD"},
        ],
    },
    {
        "id": "kindle_unlimited", "title": "Kindle Unlimited", "category": "ebooks",
        "color": "#FF9900", "text_color": "#000000",
        "url": "https://www.amazon.com/kindle-dbs/hz/subscribe/ku",
        "description": "Más de 4 millones de ebooks, audiolibros y revistas incluidos",
        "plans": [
            {"name": "Kindle Unlimited", "price": 11.99, "currency": "USD"},
        ],
    },
    {
        "id": "scribd", "title": "Scribd", "category": "ebooks",
        "color": "#1E7B85", "text_color": "#ffffff",
        "url": "https://www.scribd.com",
        "description": "Ebooks, audiolibros, podcasts y documentos académicos",
        "plans": [
            {"name": "Scribd All Access", "price": 11.99, "currency": "USD"},
        ],
    },
    # ── Software y Herramientas ───────────────────────
    {
        "id": "microsoft_365", "title": "Microsoft 365", "category": "software",
        "color": "#0078D4", "text_color": "#ffffff",
        "url": "https://www.microsoft.com/microsoft-365",
        "description": "Word, Excel, PowerPoint, Teams, OneDrive y más",
        "plans": [
            {"name": "Personal",             "price": 6.99, "currency": "USD"},
            {"name": "Familiar (6 usuarios)", "price": 9.99, "currency": "USD"},
        ],
    },
    {
        "id": "adobe_cc", "title": "Adobe Creative Cloud", "category": "software",
        "color": "#FF0000", "text_color": "#ffffff",
        "url": "https://www.adobe.com/creativecloud",
        "description": "Photoshop, Illustrator, Premiere, After Effects y más de 20 apps",
        "plans": [
            {"name": "Photography",  "price": 9.99,  "currency": "USD"},
            {"name": "All Apps",     "price": 54.99, "currency": "USD"},
        ],
    },
    {
        "id": "notion", "title": "Notion", "category": "software",
        "color": "#000000", "text_color": "#ffffff",
        "url": "https://www.notion.so",
        "description": "Notas, base de datos, gestión de proyectos y wiki colaborativo",
        "plans": [
            {"name": "Plus",     "price": 10.00, "currency": "USD"},
            {"name": "Business", "price": 18.00, "currency": "USD"},
        ],
    },
]

STREAMING_SERVICES = [
    # ── Streaming ─────────────────────────────────────────────
    {
        "id": "netflix", "title": "Netflix", "category": "streaming",
        "color": "#E50914", "text_color": "#ffffff",
        "url": "https://www.netflix.com/signup",
        "description": "Series, películas y documentales en streaming",
        "plans": [
            {"name": "Estándar con Anuncios", "price": 7.99,  "currency": "USD"},
            {"name": "Estándar",               "price": 15.49, "currency": "USD"},
            {"name": "Premium",                "price": 22.99, "currency": "USD"},
        ],
    },
    {
        "id": "prime_video", "title": "Amazon Prime Video", "category": "streaming",
        "color": "#00A8E1", "text_color": "#ffffff",
        "url": "https://www.primevideo.com",
        "description": "Películas, series y contenido original de Amazon",
        "plans": [
            {"name": "Prime Video",                   "price": 8.99,  "currency": "USD"},
            {"name": "Amazon Prime (+ envíos gratis)", "price": 14.99, "currency": "USD"},
        ],
    },
    {
        "id": "disney_plus", "title": "Disney+", "category": "streaming",
        "color": "#1435A0", "text_color": "#ffffff",
        "url": "https://www.disneyplus.com",
        "description": "Disney, Marvel, Star Wars y National Geographic",
        "plans": [
            {"name": "Básico",   "price": 7.99,  "currency": "USD"},
            {"name": "Premium",  "price": 13.99, "currency": "USD"},
        ],
    },
    {
        "id": "hbo_max", "title": "Max (HBO)", "category": "streaming",
        "color": "#5722CC", "text_color": "#ffffff",
        "url": "https://www.max.com",
        "description": "Series HBO, películas Warner y contenido exclusivo",
        "plans": [
            {"name": "Con Anuncios", "price": 9.99,  "currency": "USD"},
            {"name": "Sin Anuncios", "price": 15.99, "currency": "USD"},
            {"name": "Ultimate",     "price": 19.99, "currency": "USD"},
        ],
    },
    {
        "id": "hulu", "title": "Hulu", "category": "streaming",
        "color": "#1CE783", "text_color": "#0b0d12",
        "url": "https://www.hulu.com/subscribe",
        "description": "Series, películas, TV en vivo y contenido original",
        "plans": [
            {"name": "Con Anuncios", "price": 7.99,  "currency": "USD"},
            {"name": "Sin Anuncios", "price": 17.99, "currency": "USD"},
        ],
    },
    {
        "id": "crunchyroll", "title": "Crunchyroll", "category": "streaming",
        "color": "#F47521", "text_color": "#ffffff",
        "url": "https://www.crunchyroll.com/welcome",
        "description": "La plataforma líder de anime en streaming",
        "plans": [
            {"name": "Fan",          "price": 7.99,  "currency": "USD"},
            {"name": "Mega Fan",     "price": 9.99,  "currency": "USD"},
            {"name": "Ultimate Fan", "price": 14.99, "currency": "USD"},
        ],
    },
    # ── Gaming Pass ───────────────────────────────────────────
    {
        "id": "xbox_gamepass", "title": "Xbox Game Pass", "category": "gaming",
        "color": "#107C10", "text_color": "#ffffff",
        "url": "https://www.xbox.com/xbox-game-pass",
        "description": "Cientos de juegos en Xbox, PC y Cloud Gaming",
        "plans": [
            {"name": "PC Game Pass",          "price": 9.99,  "currency": "USD"},
            {"name": "Game Pass Ultimate",    "price": 19.99, "currency": "USD"},
        ],
    },
    {
        "id": "ea_play", "title": "EA Play", "category": "gaming",
        "color": "#FF4747", "text_color": "#ffffff",
        "url": "https://www.ea.com/ea-play",
        "description": "Más de 100 juegos de EA: FIFA, Battlefield y más",
        "plans": [
            {"name": "EA Play",     "price": 4.99,  "currency": "USD"},
            {"name": "EA Play Pro", "price": 14.99, "currency": "USD"},
        ],
    },
    {
        "id": "ps_plus", "title": "PlayStation Plus", "category": "gaming",
        "color": "#003087", "text_color": "#ffffff",
        "url": "https://www.playstation.com/ps-plus",
        "description": "Juegos mensuales gratis, multijugador online y catálogo",
        "plans": [
            {"name": "Essential", "price": 9.99,  "currency": "USD"},
            {"name": "Extra",     "price": 14.99, "currency": "USD"},
            {"name": "Premium",   "price": 17.99, "currency": "USD"},
        ],
    },
    {
        "id": "apple_arcade", "title": "Apple Arcade", "category": "gaming",
        "color": "#555555", "text_color": "#ffffff",
        "url": "https://www.apple.com/apple-arcade",
        "description": "Más de 200 juegos premium sin anuncios ni compras adicionales",
        "plans": [
            {"name": "Individual", "price": 6.99, "currency": "USD"},
            {"name": "Familiar",   "price": 9.99, "currency": "USD"},
        ],
    },
]


def _fetch_page(offset: int, limit: int = 100) -> dict:
    params = {
        "key":      ITAD_KEY,
        "limit":    limit,
        "offset":   offset,
        "country":  "US",
        "sort":     "-cut",
        "nondeals": False,
    }
    for attempt in range(3):
        try:
            resp = SESSION.get(
                f"{ITAD_API}/deals/v2",
                params=params,
                timeout=15,
            )
            print(f"[Offset {offset}] Status: {resp.status_code}")
            if resp.status_code == 429:
                wait = 2 ** attempt
                print(f"[Offset {offset}] Rate limited, waiting {wait}s")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"[Offset {offset}] Attempt {attempt+1} failed: {e}")
            time.sleep(1)
    return {"list": [], "hasMore": False}


def _parse_deal(item: dict) -> dict:
    deal        = item.get("deal") or {}
    shop        = deal.get("shop") or {}
    price       = deal.get("price") or {}
    regular     = deal.get("regular") or {}
    assets      = item.get("assets") or {}
    store_low   = deal.get("storeLow") or {}
    history_low = deal.get("historyLow") or {}

    # Prefer higher-res banner600; fall back to boxart, banner300, then ITAD CDN
    game_id = item.get("id") or ""
    thumb = (
        assets.get("banner600")
        or assets.get("boxart")
        or assets.get("banner300")
        or (f"https://assets.isthereanydeal.com/{game_id}/banner600.jpg" if game_id else "")
    )

    return {
        "id":             item.get("id") or "",
        "name":           item.get("title") or "Unknown",
        "price":          float(price.get("amount") or 0),
        "original_price": float(regular.get("amount") or 0),
        "discount":       int(deal.get("cut") or 0),
        "store":          shop.get("name") or "Unknown",
        "store_id":       str(shop.get("id") or ""),
        "url":            deal.get("url") or "",
        "thumb":          thumb,
        "metacritic":     0,
        "steam_rating":   0,
        "store_low":      float(store_low.get("amount") or 0),
        "history_low":    float(history_low.get("amount") or 0),
        "flag":           deal.get("flag"),
        "expiry":         deal.get("expiry"),
        "voucher":        deal.get("voucher"),
        "currency":       price.get("currency") or "USD",
        "category":       "license" if (shop.get("name") or "") in LICENSE_STORES else "game",
    }


def scrape_deals(pages: int = 5) -> list:
    if not ITAD_KEY:
        print("[scraper] ERROR: ITAD_API_KEY no configurada.")
        return []

    seen  = set()
    deals = []
    limit = 100

    for page in range(pages):
        offset = page * limit
        data   = _fetch_page(offset, limit)
        raw    = data.get("list") or []

        if page == 0 and raw:
            first = raw[0]
            d = first.get("deal") or {}
            print(f"[debug] title={first.get('title')} | cut={d.get('cut')} | price={d.get('price', {}).get('amount')}")

        for item in raw:
            title = (item.get("title") or "").strip().lower()
            cut   = int((item.get("deal") or {}).get("cut") or 0)

            if not title or title in seen or cut <= 0:
                continue

            seen.add(title)
            deals.append(_parse_deal(item))

        if not data.get("hasMore"):
            break

        if page < pages - 1:
            time.sleep(0.4)

    print(f"[scraper] Total unique deals: {len(deals)}")
    return deals


def scrape_popular(count: int = 12) -> list:
    if not ITAD_KEY:
        return []

    try:
        resp = SESSION.get(
            f"{ITAD_API}/stats/most-popular/v1",
            params={"key": ITAD_KEY, "limit": count + 10},
            timeout=15,
        )
        resp.raise_for_status()
        ranked = resp.json()
    except Exception as e:
        print(f"[popular] Error fetching ranked: {e}")
        return []

    games = [g for g in ranked if g.get("type") == "game" and not g.get("mature")][:count]
    if not games:
        return []

    game_ids   = [g["id"] for g in games]
    id_to_info = {g["id"]: g for g in games}

    try:
        resp = SESSION.post(
            f"{ITAD_API}/games/overview/v2",
            params={"key": ITAD_KEY, "country": "US"},
            json=game_ids,
            timeout=15,
        )
        resp.raise_for_status()
        overview = resp.json()
    except Exception as e:
        print(f"[popular] Error fetching overview: {e}")
        overview = {"prices": []}

    id_to_price = {p["id"]: p for p in (overview.get("prices") or [])}

    result = []
    for gid in game_ids:
        info     = id_to_info.get(gid) or {}
        pdata    = id_to_price.get(gid) or {}
        current  = pdata.get("current") or {}
        shop     = current.get("shop") or {}
        price    = current.get("price") or {}
        itad_url = (pdata.get("urls") or {}).get("game") or \
                   f"https://isthereanydeal.com/game/{info.get('slug', gid)}/"

        result.append({
            "id":       gid,
            "title":    info.get("title") or "Unknown",
            "banner":   f"https://assets.isthereanydeal.com/{gid}/banner600.jpg",
            "price":    float(price.get("amount") or 0),
            "currency": price.get("currency") or "USD",
            "cut":      int(current.get("cut") or 0),
            "store":    shop.get("name") or "",
            "url":      current.get("url") or itad_url,
            "itad_url": itad_url,
            "on_sale":  bool(current and int(current.get("cut") or 0) > 0),
        })

    print(f"[popular] {len(result)} featured games")
    return result


def _parse_owners(owners_str: str) -> int:
    """Parse '1,000,000 .. 2,000,000' → 1000000 (lower bound)."""
    try:
        return int(owners_str.split("..")[0].replace(",", "").strip())
    except Exception:
        return 0


def scrape_steamspy_deals() -> tuple[list, dict]:
    """Fetch discounted Steam games from SteamSpy top100in2weeks.

    Returns (deals_list, popularity_map) where popularity_map maps
    name_lower → owner_count for ALL 100 entries (not just discounted ones).
    """
    try:
        resp = SESSION.get(
            STEAMSPY_API,
            params={"request": "top100in2weeks"},
            timeout=15,
        )
        resp.raise_for_status()
        raw = resp.json()
    except Exception as e:
        print(f"[steamspy] Error: {e}")
        return [], {}

    deals          = []
    popularity_map = {}

    for appid_str, item in raw.items():
        try:
            appid          = int(appid_str)
            name           = (item.get("name") or "").strip()
            owners_approx  = _parse_owners(item.get("owners", ""))

            if name:
                popularity_map[name.lower()] = owners_approx

            discount   = int(item.get("discount") or 0)
            init_price = int(item.get("initialprice") or 0)
            cur_price  = int(item.get("price") or 0)

            if discount <= 0 or init_price <= 0 or not name:
                continue

            deals.append({
                "id":             f"steamspy_{appid}",
                "name":           name,
                "price":          cur_price / 100,
                "original_price": init_price / 100,
                "discount":       discount,
                "store":          "Steam",
                "store_id":       "steam",
                "url":            f"https://store.steampowered.com/app/{appid}",
                "thumb":          f"https://cdn.akamai.steamstatic.com/steam/apps/{appid}/header.jpg",
                "metacritic":     0,
                "steam_rating":   0,
                "store_low":      0.0,
                "history_low":    0.0,
                "flag":           None,
                "expiry":         None,
                "voucher":        None,
                "currency":       "USD",
                "category":       "game",
                "popularity":     owners_approx,
            })
        except (ValueError, TypeError):
            continue

    deals.sort(key=lambda d: d["discount"], reverse=True)
    print(f"[steamspy] {len(deals)} discounted games from top100in2weeks")
    return deals, popularity_map


def scrape_ggdeals_deals() -> list:
    """
    Fetches top-100-forever games from SteamSpy (original prices + App IDs),
    then queries GG.deals for current retail prices across all stores.
    Returns deals where a discount can be confirmed.
    """
    # Step 1 — SteamSpy top100forever for App IDs + original prices
    try:
        resp = SESSION.get(
            STEAMSPY_API,
            params={"request": "top100forever"},
            timeout=15,
        )
        resp.raise_for_status()
        raw = resp.json()
    except Exception as e:
        print(f"[ggdeals] SteamSpy top100forever failed: {e}")
        return []

    spy_map = {}
    for appid_str, item in raw.items():
        try:
            appid      = int(appid_str)
            init_cents = int(item.get("initialprice") or 0)
            name       = (item.get("name") or "").strip()
            if name and init_cents > 0:
                spy_map[appid] = {
                    "name":       name,
                    "init_price": init_cents / 100,
                    "popularity": _parse_owners(item.get("owners", "")),
                }
        except (ValueError, TypeError):
            continue

    if not spy_map:
        return []

    # Step 2 — Query GG.deals (up to 500 IDs per request; free tier = 100 req/min)
    appids = list(spy_map.keys())[:500]
    try:
        resp = SESSION.get(
            GGDEALS_API,
            params={
                "key":    GGDEALS_KEY,
                "ids":    ",".join(str(a) for a in appids),
                "region": "us",
            },
            timeout=15,
        )
        resp.raise_for_status()
        gg = resp.json()
    except Exception as e:
        print(f"[ggdeals] API fetch failed: {e}")
        return []

    if not gg.get("success"):
        msg = (gg.get("data") or {}).get("message", "unknown error")
        print(f"[ggdeals] API error: {msg}")
        return []

    # Step 3 — Build deals: use GG.deals retail price vs SteamSpy original price
    deals = []
    for appid_str, info in (gg.get("data") or {}).items():
        if not info:
            continue
        try:
            appid    = int(appid_str)
            spy      = spy_map.get(appid)
            if not spy:
                continue

            prices     = info.get("prices") or {}
            retail_str = prices.get("currentRetail")
            if retail_str is None:
                continue

            retail     = float(retail_str)
            init_price = spy["init_price"]
            if retail <= 0 or init_price <= 0:
                continue

            discount = round((1 - retail / init_price) * 100)
            if discount <= 0:
                continue

            hist_str  = prices.get("historicalRetail")
            hist_low  = float(hist_str) if hist_str else retail
            at_low    = retail <= hist_low + 0.01
            gg_url    = info.get("url") or f"https://gg.deals/steam/app/{appid}/"

            deals.append({
                "id":             f"ggdeals_{appid}",
                "name":           spy["name"],
                "price":          retail,
                "original_price": init_price,
                "discount":       discount,
                "store":          "GG.deals",
                "store_id":       "ggdeals",
                "url":            gg_url,
                "thumb":          f"https://cdn.akamai.steamstatic.com/steam/apps/{appid}/header.jpg",
                "metacritic":     0,
                "steam_rating":   0,
                "store_low":      hist_low,
                "history_low":    hist_low,
                "flag":           "H" if at_low else None,
                "expiry":         None,
                "voucher":        None,
                "currency":       "USD",
                "category":       "game",
                "popularity":     spy.get("popularity", 0),
            })
        except (ValueError, TypeError, KeyError):
            continue

    deals.sort(key=lambda d: d["discount"], reverse=True)
    print(f"[ggdeals] {len(deals)} discounted games from top100forever")
    return deals


def scrape_bundles() -> list:
    """Scrape active game bundles from Humble Bundle and Fanatical."""
    bundles = []

    # ── Humble Bundle ─────────────────────────────────────────────────────────
    try:
        resp = SESSION.get(
            "https://www.humblebundle.com/bundles",
            headers={**HEADERS, "Accept": "text/html"},
            timeout=15,
        )
        if resp.ok:
            import re as _re
            m = _re.search(r'data-js-payloads="([^"]+)"', resp.text)
            if not m:
                m = _re.search(r'"mosaic"\s*:\s*(\[.+?\])\s*,\s*"[a-z]', resp.text, _re.DOTALL)
            if m:
                import json as _json, html as _html
                raw = _html.unescape(m.group(1))
                try:
                    payload = _json.loads(raw)
                    mosaic = payload.get("mosaic") or []
                    for section in mosaic:
                        for product in (section.get("products") or []):
                            tile = product.get("tile_short_name") or ""
                            name = product.get("human_name") or tile
                            if not name:
                                continue
                            end_at = product.get("end_date") or product.get("start_date_datetime_object")
                            bundles.append({
                                "name":     name,
                                "store":    "Humble Bundle",
                                "url":      f"https://www.humblebundle.com/games/{tile}" if tile else "https://www.humblebundle.com/bundles",
                                "image":    product.get("high_res_tile_image") or product.get("tile_image") or "",
                                "end_date": str(end_at)[:10] if end_at else "",
                                "tiers":    len(product.get("tiers") or []),
                                "from_price": float((product.get("tiers") or [{}])[0].get("price", {}).get("amount", 1)) if product.get("tiers") else 1.0,
                            })
                except Exception:
                    pass
    except Exception as e:
        print(f"[bundles] Humble error: {e}")

    # ── Fanatical ─────────────────────────────────────────────────────────────
    try:
        resp = SESSION.get(
            "https://www.fanatical.com/api/page/bundle",
            headers={**HEADERS, "Accept": "application/json"},
            timeout=12,
        )
        if resp.ok:
            data = resp.json()
            for item in (data.get("hits") or []):
                name = item.get("name") or item.get("slug") or ""
                if not name:
                    continue
                slug = item.get("slug") or ""
                bundles.append({
                    "name":       name,
                    "store":      "Fanatical",
                    "url":        f"https://www.fanatical.com/en/bundle/{slug}" if slug else "https://www.fanatical.com/en/bundle",
                    "image":      (item.get("cover") or {}).get("url") or "",
                    "end_date":   (item.get("endDate") or "")[:10],
                    "tiers":      len(item.get("tiers") or []),
                    "from_price": float((item.get("tiers") or [{}])[0].get("price", 1)) if item.get("tiers") else float(item.get("price") or 1),
                })
    except Exception as e:
        print(f"[bundles] Fanatical error: {e}")

    print(f"[bundles] {len(bundles)} active bundles")
    return bundles


def _search_rawg_id(name: str) -> int | None:
    if not RAWG_KEY:
        return None
    try:
        resp = SESSION.get(
            f"{RAWG_API}/games",
            params={"key": RAWG_KEY, "search": name, "page_size": 5},
            timeout=10,
        )
        resp.raise_for_status()
        results = resp.json().get("results") or []
        return results[0]["id"] if results else None
    except Exception as e:
        print(f"[rawg_search] Error: {e}")
        return None


def fetch_rawg_game_detail(name: str) -> dict | None:
    """Search RAWG by name and return full game detail dict, or None."""
    game_id = _search_rawg_id(name)
    if not game_id:
        return None
    try:
        resp = SESSION.get(
            f"{RAWG_API}/games/{game_id}",
            params={"key": RAWG_KEY},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"[rawg_detail] Error: {e}")
        return None

    try:
        ss_resp = SESSION.get(
            f"{RAWG_API}/games/{game_id}/screenshots",
            params={"key": RAWG_KEY, "page_size": 8},
            timeout=10,
        )
        ss_resp.raise_for_status()
        screenshots = [s["image"] for s in (ss_resp.json().get("results") or [])]
    except Exception:
        screenshots = []

    _SAFE_TAGS = ['b', 'i', 'strong', 'em', 'br', 'p', 'ul', 'ol', 'li', 'span']
    pc_min = pc_rec = ""
    for p in data.get("platforms") or []:
        if (p.get("platform") or {}).get("slug") == "pc":
            req = p.get("requirements") or {}
            pc_min = bleach.clean(req.get("minimum") or "", tags=_SAFE_TAGS, strip=True)
            pc_rec = bleach.clean(req.get("recommended") or "", tags=_SAFE_TAGS, strip=True)
            break

    platforms = [
        (p.get("platform") or {}).get("name")
        for p in (data.get("platforms") or [])
        if (p.get("platform") or {}).get("name")
    ]

    return {
        "id":           data.get("id"),
        "name":         data.get("name") or "",
        "description":  data.get("description_raw") or "",
        "released":     data.get("released") or "",
        "background":   _safe_url(data.get("background_image")),
        "background2":  _safe_url(data.get("background_image_additional")),
        "website":      _safe_url(data.get("website")),
        "rating":       round(float(data.get("rating") or 0), 1),
        "ratings_count": data.get("ratings_count") or 0,
        "ratings":      data.get("ratings") or [],
        "metacritic":   data.get("metacritic"),
        "metacritic_platforms": data.get("metacritic_platforms") or [],
        "platforms":    platforms,
        "genres":       [g["name"] for g in (data.get("genres") or [])],
        "tags":         [t["name"] for t in (data.get("tags") or [])[:12]],
        "developers":   [d["name"] for d in (data.get("developers") or [])],
        "publishers":   [p["name"] for p in (data.get("publishers") or [])],
        "esrb":         (data.get("esrb_rating") or {}).get("name") or "",
        "pc_min":       pc_min,
        "pc_rec":       pc_rec,
        "screenshots":  screenshots,
        "slug":         data.get("slug") or "",
    }


def scrape_rawg_popular(count: int = 20) -> list:
    """Fetches trending recent games from RAWG (ordered by player additions)."""
    if not RAWG_KEY:
        return []
    from datetime import date, timedelta
    end   = date.today().isoformat()
    start = (date.today() - timedelta(days=365)).isoformat()
    try:
        resp = SESSION.get(
            f"{RAWG_API}/games",
            params={
                "key":       RAWG_KEY,
                "ordering":  "-added",
                "dates":     f"{start},{end}",
                "page_size": count,
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"[rawg] Error: {e}")
        return []

    result = []
    for g in data.get("results") or []:
        steam_url = ""
        for s in g.get("stores") or []:
            if (s.get("store") or {}).get("slug") == "steam":
                steam_url = s.get("url") or ""
                break
        genres = [genre["name"] for genre in (g.get("genres") or [])][:3]
        result.append({
            "id":         g.get("id"),
            "name":       g.get("name") or "Unknown",
            "image":      _safe_url(g.get("background_image")),
            "rating":     round(float(g.get("rating") or 0), 1),
            "metacritic": g.get("metacritic"),
            "released":   (g.get("released") or "")[:4],
            "genres":     genres,
            "url":        steam_url or f"https://rawg.io/games/{g.get('slug', g.get('id'))}",
        })
    print(f"[rawg] {len(result)} trending games")
    return result


def scrape_subscriptions(game_ids: list) -> dict:
    """Returns {game_id: [sub_list]} for games currently in subscription services."""
    if not ITAD_KEY or not game_ids:
        return {}

    result = {}
    # ITAD accepts max 200 IDs per request for /games/subs/v1
    chunk_size = 200
    for i in range(0, len(game_ids), chunk_size):
        chunk = game_ids[i:i + chunk_size]
        try:
            resp = SESSION.post(
                f"{ITAD_API}/games/subs/v1",
                params={"key": ITAD_KEY, "country": "US"},
                json=chunk,
                timeout=15,
            )
            if not resp.ok:
                print(f"[subs] Error {resp.status_code}: {resp.text[:300]}")
                continue
            for item in resp.json():
                if item.get("subs"):
                    result[item["id"]] = item["subs"]
        except Exception as e:
            print(f"[subs] Error: {e}")

    print(f"[subs] {len(result)} games in subscription services")
    return result


def lookup_itad_id(title: str) -> str | None:
    """Return the ITAD game UUID for a given title, or None if not found."""
    if not ITAD_KEY or not title:
        return None
    try:
        resp = SESSION.get(
            f"{ITAD_API}/games/lookup/v1",
            params={"key": ITAD_KEY, "title": title},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("found"):
            return (data.get("game") or {}).get("id")
    except Exception as e:
        print(f"[itad_lookup] Error for '{title}': {e}")
    return None


def fetch_game_offers(itad_id: str) -> list:
    """Fetch current prices across all stores for a game via ITAD /games/prices/v3."""
    if not ITAD_KEY or not itad_id:
        return []
    try:
        resp = SESSION.post(
            f"{ITAD_API}/games/prices/v3",
            params={"key": ITAD_KEY, "country": "US"},
            json=[itad_id],
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"[game_offers] Error: {e}")
        return []

    offers = []
    for game in (data if isinstance(data, list) else []):
        for deal in (game.get("deals") or []):
            shop    = deal.get("shop") or {}
            price   = deal.get("price") or {}
            regular = deal.get("regular") or {}
            offers.append({
                "store":    shop.get("name") or "Unknown",
                "price":    float(price.get("amount") or 0),
                "original": float(regular.get("amount") or 0),
                "cut":      int(deal.get("cut") or 0),
                "currency": price.get("currency") or "USD",
                "url":      deal.get("url") or "",
                "expiry":   deal.get("expiry"),
                "voucher":  deal.get("voucher"),
                "flag":     deal.get("flag"),
            })

    offers.sort(key=lambda o: o["price"])
    print(f"[game_offers] {len(offers)} store prices for {itad_id}")
    return offers


def fetch_game_dlcs(rawg_id: int) -> list:
    """Fetch DLCs/expansions for a game via RAWG /games/{id}/additions."""
    if not RAWG_KEY or not rawg_id:
        return []
    try:
        resp = SESSION.get(
            f"{RAWG_API}/games/{rawg_id}/additions",
            params={"key": RAWG_KEY, "page_size": 20},
            timeout=10,
        )
        resp.raise_for_status()
        results = resp.json().get("results") or []
    except Exception as e:
        print(f"[game_dlcs] Error: {e}")
        return []

    dlcs = []
    for g in results:
        dlcs.append({
            "name":       g.get("name") or "",
            "slug":       g.get("slug") or "",
            "background": _safe_url(g.get("background_image")),
            "released":   (g.get("released") or "")[:4],
            "rating":     round(float(g.get("rating") or 0), 1),
            "metacritic": g.get("metacritic"),
        })
    print(f"[game_dlcs] {len(dlcs)} DLCs for rawg_id={rawg_id}")
    return dlcs


def fetch_game_articles(rawg_id: int) -> list:
    """Fetch Reddit posts for a game via RAWG /games/{id}/reddit."""
    if not RAWG_KEY or not rawg_id:
        return []
    try:
        resp = SESSION.get(
            f"{RAWG_API}/games/{rawg_id}/reddit",
            params={"key": RAWG_KEY, "page_size": 12},
            timeout=10,
        )
        resp.raise_for_status()
        results = resp.json().get("results") or []
    except Exception as e:
        print(f"[game_articles] Error: {e}")
        return []

    articles = []
    for post in results:
        articles.append({
            "name":     post.get("name") or "",
            "text":     post.get("text") or "",
            "url":      post.get("url") or "",
            "image":    post.get("image") or "",
            "username": post.get("username") or "",
            "created":  post.get("created") or "",
        })
    print(f"[game_articles] {len(articles)} articles for rawg_id={rawg_id}")
    return articles


def fetch_game_streams(rawg_id: int) -> list:
    """Fetch Twitch stream entries for a game via RAWG /games/{id}/twitch."""
    if not RAWG_KEY or not rawg_id:
        return []
    try:
        resp = SESSION.get(
            f"{RAWG_API}/games/{rawg_id}/twitch",
            params={"key": RAWG_KEY, "page_size": 12},
            timeout=10,
        )
        resp.raise_for_status()
        results = resp.json().get("results") or []
    except Exception as e:
        print(f"[game_streams] Error: {e}")
        return []

    streams = []
    for s in results:
        streams.append({
            "name":        s.get("name") or "",
            "description": s.get("description") or "",
            "thumbnail":   s.get("thumbnail_url") or "",
            "view_count":  s.get("view_count") or 0,
            "language":    s.get("language") or "",
            "created":     s.get("created") or "",
            "external_id": str(s.get("external_id") or ""),
        })
    print(f"[game_streams] {len(streams)} streams for rawg_id={rawg_id}")
    return streams


def fetch_game_similar(rawg_id: int) -> list:
    """Fetch similar / series games via RAWG /games/{id}/suggested and game-series."""
    if not RAWG_KEY or not rawg_id:
        return []

    results = []
    try:
        resp = SESSION.get(
            f"{RAWG_API}/games/{rawg_id}/suggested",
            params={"key": RAWG_KEY, "page_size": 12},
            timeout=10,
        )
        if resp.ok:
            results = resp.json().get("results") or []
    except Exception as e:
        print(f"[game_similar] suggested Error: {e}")

    if len(results) < 4:
        try:
            resp2 = SESSION.get(
                f"{RAWG_API}/games/{rawg_id}/game-series",
                params={"key": RAWG_KEY, "page_size": 12},
                timeout=10,
            )
            if resp2.ok:
                seen   = {g["id"] for g in results}
                series = resp2.json().get("results") or []
                results += [g for g in series if g.get("id") not in seen]
        except Exception as e:
            print(f"[game_similar] game-series Error: {e}")

    games = []
    for g in results[:12]:
        genres = [genre["name"] for genre in (g.get("genres") or [])][:3]
        games.append({
            "name":       g.get("name") or "",
            "slug":       g.get("slug") or "",
            "background": _safe_url(g.get("background_image")),
            "rating":     round(float(g.get("rating") or 0), 1),
            "metacritic": g.get("metacritic"),
            "released":   (g.get("released") or "")[:4],
            "genres":     genres,
        })
    print(f"[game_similar] {len(games)} similar games for rawg_id={rawg_id}")
    return games


def _parse_itad_ts(ts_str: str) -> int | None:
    """Parse ITAD ISO timestamp (e.g. '2026-04-28T19:17:31+02:00') → Unix ms."""
    try:
        # Strip timezone offset and parse as naive UTC approximation
        clean = re.sub(r'[+-]\d{2}:\d{2}$', '', ts_str.strip())
        dt = datetime.fromisoformat(clean)
        return int(dt.replace(tzinfo=timezone.utc).timestamp() * 1000)
    except Exception:
        return None


def fetch_price_history(itad_id: str) -> dict | None:
    """Fetch price history from ITAD /games/history/v2 and compute insights.

    ITAD response is a flat list of deal-change events:
      [{"timestamp": "2026-04-28T19:17:31+02:00",
        "shop": {"id": 61, "name": "Steam"},
        "deal": {"price": {"amount": 24.99, "currency": "USD"}, "cut": 0}}, ...]
    """
    if not ITAD_KEY or not itad_id:
        return None
    try:
        resp = SESSION.get(
            f"{ITAD_API}/games/history/v2",
            params={"key": ITAD_KEY, "id": itad_id, "country": "US"},
            timeout=15,
        )
        resp.raise_for_status()
        raw = resp.json()
    except Exception as e:
        print(f"[price_history] Error: {e}")
        return None

    if not raw:
        return None

    # Prefer Steam (shop.id == 61); fall back to all entries from any shop
    steam = [e for e in raw if (e.get("shop") or {}).get("id") == 61]
    events = steam if steam else raw
    shop_name = "Steam" if steam else ((events[0].get("shop") or {}).get("name", "Desconocido"))

    points = []
    for entry in events:
        ts_ms  = _parse_itad_ts(entry.get("timestamp", ""))
        deal   = entry.get("deal") or {}
        amount = (deal.get("price") or {}).get("amount")
        cut    = int(deal.get("cut") or 0)
        currency = (deal.get("price") or {}).get("currency", "USD")

        if ts_ms is None or amount is None:
            continue
        points.append({
            "date":     ts_ms,
            "price":    round(float(amount), 2),
            "cut":      cut,
            "currency": currency,
        })

    if not points:
        return None

    points.sort(key=lambda p: p["date"])

    currency  = points[0]["currency"]
    prices    = [p["price"] for p in points]
    min_price = min(prices)
    sales     = [p for p in points if p["cut"] > 0]
    avg_discount = round(sum(p["cut"] for p in sales) / len(sales)) if sales else 0

    days_since_sale = None
    freq_label      = None
    if sales:
        last_sale_ts    = max(p["date"] for p in sales) / 1000
        days_since_sale = int((time.time() - last_sale_ts) / 86400)

        if len(sales) >= 2:
            sorted_ts = sorted(p["date"] / 1000 for p in sales)
            gaps = [
                (sorted_ts[i + 1] - sorted_ts[i]) / 86400
                for i in range(len(sorted_ts) - 1)
            ]
            avg_gap = round(sum(gaps) / len(gaps))
            freq_label = (
                f"Suele rebajarse cada ~{avg_gap} días "
                f"— última fue hace {days_since_sale} días"
            )

    return {
        "points":          points,
        "currency":        currency,
        "shop":            shop_name,
        "min_price":       min_price,
        "avg_discount":    avg_discount,
        "days_since_sale": days_since_sale,
        "freq_label":      freq_label,
    }
