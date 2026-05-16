"""Sample data used when no API keys are configured.

When ITAD_API_KEY / RAWG_API_KEY are missing, scraper functions fall back
to this static catalogue so the UI is fully browsable without external
calls. Auto-activates on a fresh clone; pegá las keys reales en .env y
los datos en vivo reemplazan a estos.
"""

_STEAM_HEADER = "https://cdn.cloudflare.steamstatic.com/steam/apps/{appid}/header.jpg"
_STEAM_HERO   = "https://cdn.cloudflare.steamstatic.com/steam/apps/{appid}/library_hero.jpg"


def _img(appid):
    return _STEAM_HEADER.format(appid=appid)


def _hero(appid):
    return _STEAM_HERO.format(appid=appid)


# Cada juego se duplica en varias tiendas para alimentar la tabla
# comparativa de la página de detalle.
_GAMES = [
    {
        "appid": 1091500, "name": "Cyberpunk 2077",
        "original": 59.99,
        "stores": [
            ("Steam",        "steam", 29.99, 50, 14.99, 14.99, "https://store.steampowered.com/app/1091500/"),
            ("GOG",          "gog",   27.49, 55, 11.99, 11.99, "https://www.gog.com/game/cyberpunk_2077"),
            ("Epic Games Store", "epic", 34.99, 42, 19.99, 19.99, "https://store.epicgames.com/en-US/p/cyberpunk-2077"),
            ("Humble Store", "humble", 31.49, 47, 14.99, 14.99, "https://www.humblebundle.com/store/cyberpunk-2077"),
        ],
        "rawg": {
            "description": "Cyberpunk 2077 is an open-world, action-adventure RPG set in Night City, a megalopolis obsessed with power, glamour and body modification. You play as V, a mercenary outlaw going after a one-of-a-kind implant that is the key to immortality.",
            "released": "2020-12-10", "rating": 4.1, "ratings_count": 7234,
            "metacritic": 76, "genres": ["RPG", "Open World", "Action"],
            "platforms": ["PC", "PS5", "Xbox Series X", "PS4", "Xbox One"],
            "developers": ["CD Projekt Red"], "publishers": ["CD Projekt"],
            "esrb": "Mature", "tags": ["Cyberpunk", "Sci-fi", "Open World", "RPG", "Story-rich", "First-person"],
            "ratings": [
                {"title": "exceptional", "percent": 52.0, "count": 3761},
                {"title": "recommended", "percent": 30.0, "count": 2170},
                {"title": "meh",         "percent": 13.0, "count":  940},
                {"title": "skip",        "percent":  5.0, "count":  363},
            ],
        },
    },
    {
        "appid": 292030, "name": "The Witcher 3: Wild Hunt",
        "original": 39.99,
        "stores": [
            ("Steam", "steam", 9.99, 75, 7.99, 7.99,  "https://store.steampowered.com/app/292030/"),
            ("GOG",   "gog",   7.99, 80, 5.99, 5.99,  "https://www.gog.com/game/the_witcher_3_wild_hunt"),
            ("Epic Games Store", "epic", 11.99, 70, 9.99, 9.99, "https://store.epicgames.com/en-US/p/the-witcher-3-wild-hunt"),
        ],
        "rawg": {
            "description": "The Witcher 3: Wild Hunt is a story-driven, next-generation open world role-playing game set in a visually stunning fantasy universe full of meaningful choices and impactful consequences.",
            "released": "2015-05-18", "rating": 4.66, "ratings_count": 6845,
            "metacritic": 92, "genres": ["RPG", "Adventure", "Open World"],
            "platforms": ["PC", "PS4", "Xbox One", "Switch"],
            "developers": ["CD Projekt Red"], "publishers": ["CD Projekt"],
            "esrb": "Mature", "tags": ["Open World", "Fantasy", "RPG", "Story-rich", "Atmospheric"],
            "ratings": [
                {"title": "exceptional", "percent": 73.0, "count": 4997},
                {"title": "recommended", "percent": 19.0, "count": 1301},
                {"title": "meh",         "percent":  6.0, "count":  411},
                {"title": "skip",        "percent":  2.0, "count":  136},
            ],
        },
    },
    {
        "appid": 1245620, "name": "Elden Ring",
        "original": 59.99,
        "stores": [
            ("Steam", "steam", 41.99, 30, 35.99, 35.99, "https://store.steampowered.com/app/1245620/"),
            ("Humble Store", "humble", 44.99, 25, 39.99, 39.99, "https://www.humblebundle.com/store/elden-ring"),
        ],
        "rawg": {
            "description": "Elden Ring is an action RPG developed by FromSoftware and published by Bandai Namco. The game is the result of a collaboration between Hidetaka Miyazaki and George R. R. Martin, set in a world full of mystery and peril.",
            "released": "2022-02-25", "rating": 4.45, "ratings_count": 2890,
            "metacritic": 96, "genres": ["RPG", "Action", "Souls-like"],
            "platforms": ["PC", "PS5", "Xbox Series X", "PS4", "Xbox One"],
            "developers": ["FromSoftware"], "publishers": ["Bandai Namco"],
            "esrb": "Mature", "tags": ["Souls-like", "Open World", "Difficult", "Dark Fantasy", "RPG"],
            "ratings": [
                {"title": "exceptional", "percent": 68.0, "count": 1965},
                {"title": "recommended", "percent": 22.0, "count":  636},
                {"title": "meh",         "percent":  7.0, "count":  202},
                {"title": "skip",        "percent":  3.0, "count":   87},
            ],
        },
    },
    {
        "appid": 1174180, "name": "Red Dead Redemption 2",
        "original": 59.99,
        "stores": [
            ("Steam",     "steam",   19.79, 67, 19.79, 19.79, "https://store.steampowered.com/app/1174180/"),
            ("Epic Games Store", "epic", 23.99, 60, 23.99, 23.99, "https://store.epicgames.com/en-US/p/red-dead-redemption-2"),
            ("Humble Store", "humble", 19.79, 67, 19.79, 19.79, "https://www.humblebundle.com/store/red-dead-redemption-2"),
        ],
        "rawg": {
            "description": "America, 1899. The end of the Wild West era has begun. After a robbery goes badly wrong in the western town of Blackwater, Arthur Morgan and the Van der Linde gang are forced to flee.",
            "released": "2019-12-05", "rating": 4.59, "ratings_count": 4521,
            "metacritic": 93, "genres": ["Action", "Adventure", "Open World"],
            "platforms": ["PC", "PS4", "Xbox One"],
            "developers": ["Rockstar Games"], "publishers": ["Rockstar Games"],
            "esrb": "Mature", "tags": ["Open World", "Western", "Story-rich", "Realistic", "Atmospheric"],
            "ratings": [
                {"title": "exceptional", "percent": 70.0, "count": 3165},
                {"title": "recommended", "percent": 19.0, "count":  860},
                {"title": "meh",         "percent":  8.0, "count":  362},
                {"title": "skip",        "percent":  3.0, "count":  136},
            ],
        },
    },
    {
        "appid": 367520, "name": "Hollow Knight",
        "original": 14.99,
        "stores": [
            ("Steam", "steam", 7.49, 50, 7.49, 7.49, "https://store.steampowered.com/app/367520/"),
            ("GOG",   "gog",   7.49, 50, 7.49, 7.49, "https://www.gog.com/game/hollow_knight"),
        ],
        "rawg": {
            "description": "Forge your own path in Hollow Knight! An epic action adventure through a vast ruined kingdom of insects and heroes. Explore twisting caverns, ancient cities and deadly wastes.",
            "released": "2017-02-24", "rating": 4.42, "ratings_count": 3201,
            "metacritic": 90, "genres": ["Metroidvania", "Indie", "Adventure"],
            "platforms": ["PC", "Switch", "PS4", "Xbox One"],
            "developers": ["Team Cherry"], "publishers": ["Team Cherry"],
            "esrb": "Everyone 10+", "tags": ["Metroidvania", "2D", "Difficult", "Indie", "Atmospheric"],
            "ratings": [
                {"title": "exceptional", "percent": 65.0, "count": 2081},
                {"title": "recommended", "percent": 24.0, "count":  768},
                {"title": "meh",         "percent":  8.0, "count":  256},
                {"title": "skip",        "percent":  3.0, "count":   96},
            ],
        },
    },
    {
        "appid": 413150, "name": "Stardew Valley",
        "original": 14.99,
        "stores": [
            ("Steam", "steam", 11.24, 25, 9.74, 9.74, "https://store.steampowered.com/app/413150/"),
            ("GOG",   "gog",   11.24, 25, 9.74, 9.74, "https://www.gog.com/game/stardew_valley"),
        ],
        "rawg": {
            "description": "You've inherited your grandfather's old farm plot in Stardew Valley. Armed with hand-me-down tools and a few coins, you set out to begin your new life.",
            "released": "2016-02-26", "rating": 4.42, "ratings_count": 2580,
            "metacritic": 89, "genres": ["Indie", "Simulation", "RPG"],
            "platforms": ["PC", "Switch", "PS4", "Xbox One", "iOS", "Android"],
            "developers": ["ConcernedApe"], "publishers": ["ConcernedApe"],
            "esrb": "Everyone 10+", "tags": ["Farming", "Pixel Graphics", "Relaxing", "Indie", "Cozy"],
            "ratings": [
                {"title": "exceptional", "percent": 60.0, "count": 1548},
                {"title": "recommended", "percent": 27.0, "count":  696},
                {"title": "meh",         "percent":  9.0, "count":  232},
                {"title": "skip",        "percent":  4.0, "count":  103},
            ],
        },
    },
    {
        "appid": 1145360, "name": "Hades",
        "original": 24.99,
        "stores": [
            ("Steam", "steam",      12.49, 50, 9.99, 9.99, "https://store.steampowered.com/app/1145360/"),
            ("Epic Games Store", "epic", 14.99, 40, 12.49, 12.49, "https://store.epicgames.com/en-US/p/hades"),
        ],
        "rawg": {
            "description": "Defy the god of the dead as you hack and slash out of the Underworld in this rogue-like dungeon crawler from the creators of Bastion, Transistor, and Pyre.",
            "released": "2020-09-17", "rating": 4.34, "ratings_count": 1820,
            "metacritic": 93, "genres": ["Indie", "Action", "Roguelike"],
            "platforms": ["PC", "Switch", "PS5", "PS4", "Xbox Series X", "Xbox One"],
            "developers": ["Supergiant Games"], "publishers": ["Supergiant Games"],
            "esrb": "Teen", "tags": ["Roguelike", "Mythology", "Action", "Indie", "Story-rich"],
            "ratings": [
                {"title": "exceptional", "percent": 63.0, "count": 1147},
                {"title": "recommended", "percent": 25.0, "count":  455},
                {"title": "meh",         "percent":  8.0, "count":  145},
                {"title": "skip",        "percent":  4.0, "count":   73},
            ],
        },
    },
    {
        "appid": 632470, "name": "Disco Elysium",
        "original": 39.99,
        "stores": [
            ("Steam", "steam", 9.99, 75, 9.99, 9.99, "https://store.steampowered.com/app/632470/"),
            ("GOG",   "gog",   7.99, 80, 7.99, 7.99, "https://www.gog.com/game/disco_elysium"),
        ],
        "rawg": {
            "description": "Disco Elysium - The Final Cut is a groundbreaking role playing game. You're a detective with a unique skill system at your disposal and a whole city block to carve your path across.",
            "released": "2019-10-15", "rating": 4.48, "ratings_count": 1320,
            "metacritic": 91, "genres": ["RPG", "Indie", "Adventure"],
            "platforms": ["PC", "Switch", "PS5", "PS4", "Xbox Series X", "Xbox One"],
            "developers": ["ZA/UM"], "publishers": ["ZA/UM"],
            "esrb": "Mature", "tags": ["Detective", "Story-rich", "RPG", "Indie", "Atmospheric"],
            "ratings": [
                {"title": "exceptional", "percent": 66.0, "count": 871},
                {"title": "recommended", "percent": 21.0, "count": 277},
                {"title": "meh",         "percent":  8.0, "count": 106},
                {"title": "skip",        "percent":  5.0, "count":  66},
            ],
        },
    },
]


def _make_deal(g, store_idx):
    store_name, store_slug, price, cut, store_low, hist_low, url = g["stores"][store_idx]
    return {
        "id":             f"demo_{g['appid']}_{store_slug}",
        "name":           g["name"],
        "price":          price,
        "original_price": g["original"],
        "discount":       cut,
        "store":          store_name,
        "store_id":       store_slug,
        "url":            url,
        "thumb":          _img(g["appid"]),
        "metacritic":     g["rawg"].get("metacritic") or 0,
        "steam_rating":   0,
        "store_low":      store_low,
        "history_low":    hist_low,
        "flag":           "H" if cut >= 70 else None,
        "expiry":         None,
        "voucher":        None,
        "currency":       "USD",
        "category":       "game",
    }


def demo_deals():
    """All sample deals (one row per store per game)."""
    out = []
    for g in _GAMES:
        for i in range(len(g["stores"])):
            out.append(_make_deal(g, i))
    return out


def demo_popular(count=12):
    """Sample featured games for the carousel (first store of each game)."""
    out = []
    for g in _GAMES[:count]:
        s = g["stores"][0]
        store_name, _slug, price, cut, _sl, _hl, url = s
        out.append({
            "id":       f"demo_{g['appid']}",
            "title":    g["name"],
            "banner":   _hero(g["appid"]),
            "price":    price,
            "currency": "USD",
            "cut":      cut,
            "store":    store_name,
            "url":      url,
            "itad_url": url,
            "on_sale":  cut > 0,
        })
    return out


def demo_rawg_trending(count=20):
    """Sample list for the 'Tendencia' grid on the home page."""
    out = []
    for g in _GAMES[:count]:
        r = g["rawg"]
        out.append({
            "id":         g["appid"],
            "name":       g["name"],
            "image":      _hero(g["appid"]),
            "rating":     r.get("rating") or 0,
            "metacritic": r.get("metacritic"),
            "released":   (r.get("released") or "")[:4],
            "genres":     r.get("genres", [])[:3],
            "url":        g["stores"][0][6],
        })
    return out


def demo_rawg_detail(name):
    """Returns a RAWG-style detail dict for a sample game, or None."""
    key = (name or "").strip().lower()
    for g in _GAMES:
        if g["name"].lower() == key:
            r = g["rawg"]
            return {
                "id":              g["appid"],
                "name":            g["name"],
                "description":     r["description"],
                "released":        r["released"],
                "background":      _hero(g["appid"]),
                "background2":     _img(g["appid"]),
                "website":         "",
                "rating":          r["rating"],
                "ratings_count":   r["ratings_count"],
                "ratings":         r["ratings"],
                "metacritic":      r["metacritic"],
                "metacritic_platforms": [],
                "platforms":       r["platforms"],
                "genres":          r["genres"],
                "tags":            r["tags"],
                "developers":      r["developers"],
                "publishers":      r["publishers"],
                "esrb":            r["esrb"],
                "pc_min":          "Windows 10 64-bit, Intel Core i5-3570K / AMD FX-8310, 8 GB RAM, NVIDIA GeForce GTX 970 / AMD Radeon RX 470",
                "pc_rec":          "Windows 10/11 64-bit, Intel Core i7-4790 / AMD Ryzen 3 3200G, 12 GB RAM, NVIDIA GeForce GTX 1060 6GB / AMD Radeon RX 590",
                "screenshots":     [_hero(g["appid"]), _img(g["appid"])],
                "slug":            g["name"].lower().replace(" ", "-").replace(":", ""),
            }
    return None


def demo_game_names():
    return [g["name"] for g in _GAMES]
