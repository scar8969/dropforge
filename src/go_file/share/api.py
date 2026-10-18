from flask import Blueprint, Response, abort, jsonify, request, send_file

from ..models import File, ShareLink, db
from .links import check_link, create_link, register_download
from .storage import LocalStorage

bp = Blueprint("share", __name__)


@bp.post("/api/upload")
def upload() -> Response | tuple[Response, int]:
    f = request.files.get("file")
    if not f or not f.filename:
        return jsonify({"error": "no file"}), 400
    storage = LocalStorage()
    path, sha, size = storage.save(f, f.filename)
    file = File.query.filter_by(sha256=sha).first()
    if not file:
        file = File(name=f.filename, size=size, sha256=sha, storage="local", path=path)
        db.session.add(file)
        db.session.commit()
    link = create_link(
        file.id,
        request.form.get("expiry", ""),
        request.form.get("password", ""),
        int(request.form.get("max_downloads", 0) or 0),
    )
    return jsonify({"file_id": file.id, "token": link.token, "url": f"/s/{link.token}"})


@bp.get("/s/<token>")
def share_page(token: str) -> Response | tuple[Response, int]:
    link, err = check_link(token)
    if err == "bad password":
        # GET reaches here when a protected link is opened without a password.
        # check_link() cannot tell "none supplied" from "wrong", so both answer
        # need_password -- the contract the OpenAPI document promises -- rather
        # than a bare 403.
        return jsonify({"need_password": True, "url": f"/s/{token}"}), 200
    if err:
        abort(410 if err == "expired" else 403)
    return jsonify({"url": f"/dl/{token}"})


@bp.post("/s/<token>")
def unlock(token: str) -> Response:
    payload = request.get_json(force=True, silent=True) or {}
    link, err = check_link(token, payload.get("password", ""))
    if err:
        abort(403)
    return jsonify({"url": f"/dl/{token}"})


@bp.get("/dl/<token>")
def download(token: str) -> Response:
    # A protected link carries its password on the download request too: the
    # unlock call only tells the caller which URL to use, it does not mint a
    # session, so the check has to happen here as well.
    link, err = check_link(token, request.args.get("password", ""))
    if err:
        abort(403)
    ok, _detail = register_download(link)
    if not ok:
        abort(403)
    f = db.session.get(File, link.file_id)
    if f is None:
        # The row can be deleted while a link still references it; answer with
        # the same not-found an unknown token gets rather than crashing on None.
        abort(404)
    return send_file(f.path, as_attachment=True, download_name=f.name)


@bp.get("/api/files")
def list_files() -> Response:
    return jsonify(
        {
            "files": [
                {
                    "id": f.id,
                    "name": f.name,
                    "size": f.size,
                    "links": ShareLink.query.filter_by(file_id=f.id).count(),
                    "downloads": sum(
                        l.downloads for l in ShareLink.query.filter_by(file_id=f.id).all()
                    ),
                }
                for f in File.query.all()
            ]
        }
    )


@bp.delete("/api/files/<int:fid>")
def delete_file(fid: int) -> Response:
    f = db.get_or_404(File, fid)
    for l in ShareLink.query.filter_by(file_id=fid).all():
        db.session.delete(l)
    db.session.delete(f)
    db.session.commit()
    return jsonify({"status": "deleted"})
