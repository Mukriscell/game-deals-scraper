import os
import time
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


def _fetch_page(offset: int, limit: int = 60) -> dict:
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

    # Prefer higher-res banner600; fall back to boxart then banner300
    thumb = (
        assets.get("banner600")
        or assets.get("boxart")
        or assets.get("banner300")
        or ""
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
    limit = 60

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


def scrape_steamspy_deals() -> list:
    """Fetch discounted Steam games from SteamSpy top100in2weeks (no API key required)."""
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
        return []

    deals = []
    for appid_str, item in raw.items():
        try:
            appid      = int(appid_str)
            discount   = int(item.get("discount") or 0)
            init_price = int(item.get("initialprice") or 0)
            cur_price  = int(item.get("price") or 0)
            name       = (item.get("name") or "").strip()

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
            })
        except (ValueError, TypeError):
            continue

    deals.sort(key=lambda d: d["discount"], reverse=True)
    print(f"[steamspy] {len(deals)} discounted games from top100in2weeks")
    return deals


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
                spy_map[appid] = {"name": name, "init_price": init_cents / 100}
        except (ValueError, TypeError):
            continue

    if not spy_map:
        return []

    # Step 2 — Query GG.deals (max 100 IDs per request; free tier = 100 req/min)
    appids = list(spy_map.keys())[:100]
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
            })
        except (ValueError, TypeError, KeyError):
            continue

    deals.sort(key=lambda d: d["discount"], reverse=True)
    print(f"[ggdeals] {len(deals)} discounted games from top100forever")
    return deals


def scrape_subscriptions(game_ids: list) -> dict:
    """Returns {game_id: [sub_list]} for games currently in subscription services."""
    if not ITAD_KEY or not game_ids:
        return {}
    try:
        resp = SESSION.post(
            f"{ITAD_API}/games/subs/v1",
            params={"key": ITAD_KEY, "country": "US"},
            json=game_ids,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"[subs] Error: {e}")
        return {}

    result = {
        item["id"]: item["subs"]
        for item in data
        if item.get("subs")
    }
    print(f"[subs] {len(result)} games in subscription services")
    return result
