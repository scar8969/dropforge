from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class File(db.Model):
    __tablename__ = "files"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256), default="")
    size = db.Column(db.Integer, default=0)
    sha256 = db.Column(db.String(64), unique=True)
    storage = db.Column(db.String(16), default="local")
    path = db.Column(db.String(512), default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ShareLink(db.Model):
    __tablename__ = "share_links"
    id = db.Column(db.Integer, primary_key=True)
    file_id = db.Column(db.Integer, db.ForeignKey("files.id"))
    token = db.Column(db.String(16), unique=True)
    password_hash = db.Column(db.String(64), nullable=True)
    expires_at = db.Column(db.DateTime, nullable=True)
    max_downloads = db.Column(db.Integer, nullable=True)
    downloads = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class DownloadLog(db.Model):
    __tablename__ = "download_logs"
    id = db.Column(db.Integer, primary_key=True)
    link_id = db.Column(db.Integer, db.ForeignKey("share_links.id"))
    ip = db.Column(db.String(64), default="")
    at = db.Column(db.DateTime, default=datetime.utcnow)
