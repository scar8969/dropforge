import os
from pathlib import Path
from typing import Any

from flask import Flask, Response, flash, jsonify, redirect, render_template, request, url_for
from werkzeug.wrappers import Response as WerkzeugResponse

from . import paths
from .models import File, ShareLink, db
from .share.api import bp
from .share.links import check_link, create_link
from .share.storage import LocalStorage

paths.INSTANCE_DIR.mkdir(parents=True, exist_ok=True)
_UPLOAD_ROOT = Path(os.environ.get("UPLOAD_ROOT", str(paths.DATA_DIR)))
_UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)


def build_app() -> Flask:
    """Build the application: configuration, database, then routes."""
    app = Flask(__name__,
                template_folder=str(paths.TEMPLATES_DIR),
                instance_path=str(paths.INSTANCE_DIR))
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + str(paths.INSTANCE_DIR / "gofile.db")
    app.config["UPLOAD_ROOT"] = str(_UPLOAD_ROOT)
    app.secret_key = os.environ.get("SECRET_KEY", "go-file-dev-secret")
    db.init_app(app)
    with app.app_context():
        db.create_all()
    app.register_blueprint(bp)

    @app.before_request
    def _rebase_relative_storage_paths() -> None:
        """share/api.py stores File.path relative to the process CWD (./data/...).
        The page routes resolve against UPLOAD_ROOT, so make both agree."""
        for f in File.query.all():
            if f.path and not os.path.isabs(f.path):
                f.path = os.path.join(app.config["UPLOAD_ROOT"], os.path.basename(f.path))
                db.session.commit()

    @app.context_processor
    def _ctx() -> dict[str, Any]:
        return {"app_name": "\U0001F4E6 go-file", "upload_root": app.config["UPLOAD_ROOT"]}

    @app.get("/api/health")
    def health() -> Response:
        return jsonify({"status": "ok", "service": "go-file", "version": "0.1.0"})

    def _rows(limit: int | None = None) -> list[dict[str, Any]]:
        q = File.query.order_by(File.id.desc())
        if limit:
            q = q.limit(limit)
        out: list[dict[str, Any]] = []
        for f in q.all():
            links = ShareLink.query.filter_by(file_id=f.id).all()
            out.append({"f": f, "links": links,
                        "downloads": sum(l.downloads or 0 for l in links)})
        return out

    def _max_dl() -> int:
        try:
            return int(request.form.get("max_downloads") or 0)
        except ValueError:
            return 0

    @app.get("/")
    def index() -> str:
        return render_template("index.html", rows=_rows(5), total=File.query.count())

    @app.get("/files")
    def files_page() -> str:
        return render_template("files.html", rows=_rows())

    @app.post("/upload")
    def upload_page() -> WerkzeugResponse:
        up = request.files.get("file")
        if not up or not up.filename:
            flash("No file selected.", "error")
            return redirect(url_for("index"))
        storage = LocalStorage(app.config["UPLOAD_ROOT"])
        path, sha, size = storage.save(up, up.filename)
        rec = File.query.filter_by(sha256=sha).first()
        if rec is None:
            rec = File(name=up.filename, size=size, sha256=sha, storage="local", path=path)
            db.session.add(rec)
            db.session.commit()
        else:
            storage.delete(path)
        link = create_link(rec.id, request.form.get("expiry", ""),
                           request.form.get("password", ""), _max_dl())
        flash("Uploaded %s - share link /share/%s" % (rec.name, link.token), "success")
        return redirect(url_for("file_detail", fid=rec.id))

    @app.get("/f/<int:fid>")
    def file_detail(fid: int) -> str:
        f = db.get_or_404(File, fid)
        links = ShareLink.query.filter_by(file_id=fid).order_by(ShareLink.id.desc()).all()
        return render_template("file.html", f=f, links=links)

    @app.post("/f/<int:fid>/link")
    def add_link(fid: int) -> WerkzeugResponse:
        f = db.get_or_404(File, fid)
        link = create_link(f.id, request.form.get("expiry", ""),
                           request.form.get("password", ""), _max_dl())
        flash("Created share link /share/%s" % link.token, "success")
        return redirect(url_for("file_detail", fid=f.id))

    @app.post("/f/<int:fid>/delete")
    def delete_file(fid: int) -> WerkzeugResponse:
        f = db.get_or_404(File, fid)
        name, path = f.name, f.path
        for l in ShareLink.query.filter_by(file_id=fid).all():
            db.session.delete(l)
        db.session.delete(f)
        db.session.commit()
        LocalStorage(app.config["UPLOAD_ROOT"]).delete(path)
        flash("Deleted %s" % name, "success")
        return redirect(url_for("files_page"))

    @app.route("/share/<token>", methods=["GET", "POST"])
    def share_page(token: str) -> str | tuple[str, int]:
        if request.method == "POST":
            link, err = check_link(token, request.form.get("password", ""))
            if err:
                return render_template("share.html", err=err, need_password=True,
                                       link=None, f=None, token=token)
        else:
            link, err = check_link(token)
            if err == "bad password":
                return render_template("share.html", err=None, need_password=True,
                                       link=None, f=None, token=token)
            if err:
                return render_template("share.html", err=err, need_password=False,
                                       link=None, f=None, token=token), 404
        f = db.session.get(File, link.file_id)
        return render_template("share.html", err=None, need_password=False,
                               link=link, f=f, token=token)

    return app


app = build_app()

if __name__ == "__main__":  # pragma: no cover - manual development entry point
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))
