from datetime import UTC, datetime
from typing import Any

from flask_sqlalchemy import SQLAlchemy

# flask_sqlalchemy builds the declarative base lazily inside init_app and stores
# it as an instance attribute, so db.Model is invisible to a static checker and
# every db.Column below would be flagged. Binding it once, to a plainly
# Any-typed alias, keeps the rest of the module checkable; the go_file.models
# override in mypy.ini turns off disallow_subclassing_any for this module
# because the base genuinely is dynamic.
db = SQLAlchemy()
Base: Any = db.Model


def _utcnow() -> datetime:
    """Naive UTC timestamp, matching the naive DateTime columns below.

    ``datetime.utcnow()`` is deprecated since 3.12 and raises a
    ``DeprecationWarning`` on every call (verified on the 3.14 interpreter that
    runs this suite), so the default is built from an aware ``now(UTC)`` and
    stripped back to naive.
    """
    return datetime.now(UTC).replace(tzinfo=None)


class File(Base):
    __tablename__ = "files"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256), default="")
    size = db.Column(db.Integer, default=0)
    sha256 = db.Column(db.String(64), unique=True)
    storage = db.Column(db.String(16), default="local")
    path = db.Column(db.String(512), default="")
    created_at = db.Column(db.DateTime, default=_utcnow)


class ShareLink(Base):
    __tablename__ = "share_links"
    id = db.Column(db.Integer, primary_key=True)
    file_id = db.Column(db.Integer, db.ForeignKey("files.id"))
    token = db.Column(db.String(16), unique=True)
    password_hash = db.Column(db.String(64), nullable=True)
    expires_at = db.Column(db.DateTime, nullable=True)
    max_downloads = db.Column(db.Integer, nullable=True)
    downloads = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=_utcnow)


class DownloadLog(Base):
    __tablename__ = "download_logs"
    id = db.Column(db.Integer, primary_key=True)
    link_id = db.Column(db.Integer, db.ForeignKey("share_links.id"))
    ip = db.Column(db.String(64), default="")
    at = db.Column(db.DateTime, default=_utcnow)
