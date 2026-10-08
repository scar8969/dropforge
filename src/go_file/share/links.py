from datetime import datetime, timedelta

import secrets, string

_ALPHABET = string.ascii_letters + string.digits

def make_token(n=8):
    return "".join(secrets.choice(_ALPHABET) for _ in range(n))

def create_link(file_id, expiry="", password="", max_dl=0):
    from ..models import ShareLink, db

    expires = None
    if expiry:
        unit = {"h": "hours", "d": "days"}[expiry[-1]]
        expires = datetime.utcnow() + timedelta(**{unit: int(expiry[:-1])})
    pw = None
    if password:
        import hashlib
        pw = hashlib.sha256(password.encode()).hexdigest()
    link = ShareLink(file_id=file_id, token=make_token(), password_hash=pw,
                     expires_at=expires, max_downloads=max_dl or None)
    db.session.add(link); db.session.commit()
    return link

def check_link(token, password=""):
    from ..models import ShareLink, db

    link = ShareLink.query.filter_by(token=token).first()
    if not link: return None, "not found"
    if link.expires_at and link.expires_at < datetime.utcnow():
        db.session.delete(link); db.session.commit(); return None, "expired"
    if link.password_hash:
        import hashlib
        if hashlib.sha256(password.encode()).hexdigest() != link.password_hash:
            return None, "bad password"
    if link.max_downloads and link.downloads >= link.max_downloads:
        return None, "limit exceeded"
    return link, None

def register_download(link):
    if link.max_downloads and link.downloads >= link.max_downloads:
        return False, "limit exceeded"
    link.downloads += 1
    from ..models import db

    db.session.commit()
    return True, None
