import os
from urllib.parse import urlparse, parse_qs

# domain → (affiliate_param_name, env_var_name)
# Param names match each store's affiliate program docs.
# Register at each store's program and set the env var with your code.
_CONFIGS = {
    'fanatical.com':      ('aff_id',      'AFFILIATE_FANATICAL'),
    'humblebundle.com':   ('partner',     'AFFILIATE_HUMBLE'),
    'greenmangaming.com': ('affiliate',   'AFFILIATE_GMG'),
    'eneba.com':          ('uid',         'AFFILIATE_ENEBA'),
    'wingamestore.com':   ('affiliateID', 'AFFILIATE_WINGAMESTORE'),
    'gamersgate.com':     ('ref',         'AFFILIATE_GAMERSGATE'),
    'gamebillet.com':     ('affref',      'AFFILIATE_GAMEBILLET'),
    'g2a.com':            ('gtag',        'AFFILIATE_G2A'),
    'amazon.com':         ('tag',         'AFFILIATE_AMAZON'),
    'indiegala.com':      ('ref',         'AFFILIATE_INDIEGALA'),
    'nuuvem.com':         ('ref',         'AFFILIATE_NUUVEM'),
    'dlgamer.com':        ('ref',         'AFFILIATE_DLGAMER'),
    'gamesplanet.com':    ('ref',         'AFFILIATE_GAMESPLANET'),
    '2game.com':          ('ref',         'AFFILIATE_2GAME'),
}


def tag_url(url: str) -> str:
    """Append affiliate tracking parameter to a store URL if a code is configured."""
    if not url:
        return url
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if domain.startswith('www.'):
            domain = domain[4:]
        config = _CONFIGS.get(domain)
        if not config:
            return url
        param, env_var = config
        code = os.environ.get(env_var, '').strip()
        if not code:
            return url
        if param in parse_qs(parsed.query):
            return url
        sep = '&' if parsed.query else '?'
        return f"{url}{sep}{param}={code}"
    except Exception:
        return url
