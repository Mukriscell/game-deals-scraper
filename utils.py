import re

_EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')


def is_valid_email(email: str) -> bool:
    return bool(email and _EMAIL_RE.match(email))


def mask_email(email: str) -> str:
    try:
        local, domain = email.rsplit('@', 1)
        return local[0] + '***@' + domain
    except Exception:
        return '***'
