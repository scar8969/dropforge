import hashlib
import secrets
import string
from datetime import UTC, datetime, timedelta
from typing import Any

from ..errors import BadRequest

_ALPHABET = string.ascii_letters + string.digits


def make_token(n: int = 8) -> str:
    return "".join(secrets.choice(_ALPHABET) for _ in range(n))


def _parse_expiry(expiry: str) -> datetime | None:
    """Turn ``24h``/``7d`` into a naive UTC deadline.

    An expiry the operator never documented is a bad request, not a 500: the
    select box only ever offers h/d, so anything else is a caller mistake.
    """
    if not expiry:
        return None
    unit = expiry[-1]
    if unit not in {"h", "d"}:
        raise BadRequest(f"expiry must end in h or d, got {expiry!r}")
    try:
        amount = int(expiry[:-1])
    except ValueError as exc:
        raise BadRequest(f"expiry must look like 24h or 7d, got {expiry!r}") from exc
    delta = timedelta(hours=amount) if unit == "h" else timedelta(days=amount)
    return datetime.now(UTC).replace(tzinfo=None) + delta


def create_link(file_id: int, expiry: str = "", password: str = "", max_dl: int = 0) -> Any:
    from ..models import ShareLink, db

    expires = _parse_expiry(expiry)
    pw = None
    if password:
        pw = hashlib.sha256(password.encode()).hexdigest()
    link = ShareLink(
        file_id=file_id,
        token=make_token(),
        password_hash=pw,
        expires_at=expires,
        max_downloads=max_dl or None,
    )
    db.session.add(link)
    db.session.commit()
    return link


def check_link(token: str, password: str = "") -> tuple[Any, str | None]:
    from ..models import ShareLink, db

    link = ShareLink.query.filter_by(token=token).first()
    if not link:
        return None, "not found"
    if link.expires_at and link.expires_at < datetime.now(UTC).replace(tzinfo=None):
        db.session.delete(link)
        db.session.commit()
        return None, "expired"
    if link.password_hash:
        if hashlib.sha256(password.encode()).hexdigest() != link.password_hash:
            return None, "bad password"
    if link.max_downloads and link.downloads >= link.max_downloads:
        return None, "limit exceeded"
    return link, None


def register_download(link: Any) -> tuple[bool, str | None]:
    if link.max_downloads and link.downloads >= link.max_downloads:
        return False, "limit exceeded"
    link.downloads += 1
    from ..models import db

    db.session.commit()
    return True, None
