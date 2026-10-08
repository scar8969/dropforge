from ..models import File, ShareLink, db
from .links import check_link, create_link, register_download
from .storage import LocalStorage

from flask import Blueprint, jsonify, request, send_file, abort

bp = Blueprint("share", __name__)

@bp.post("/api/upload")
def upload():
    f = request.files.get("file")
    if not f:
        return jsonify({"error": "no file"}), 400
    storage = LocalStorage()
    path, sha, size = storage.save(f, f.filename)
    file = File.query.filter_by(sha256=sha).first()
    if not file:
        file = File(name=f.filename, size=size, sha256=sha, storage="local", path=path)
        db.session.add(file)
        db.session.commit()
    link = create_link(file.id, request.form.get("expiry", ""),
                       request.form.get("password", ""), int(request.form.get("max_downloads", 0) or 0))
    return jsonify({"file_id": file.id, "token": link.token, "url": f"/s/{link.token}"})

@bp.get("/s/<token>")
def share_page(token):
    link, err = check_link(token)
    if err:
        abort(410 if err == "expired" else 403)
    if link.password_hash:
        return jsonify({"need_password": True, "url": f"/s/{token}"}), 200
    return jsonify({"url": f"/dl/{token}"})

@bp.post("/s/<token>")
def unlock(token):
    payload = request.get_json(force=True, silent=True) or {}
    link, err = check_link(token, payload.get("password", ""))
    if err:
        abort(403)
    return jsonify({"url": f"/dl/{token}"})

@bp.get("/dl/<token>")
def download(token):
    link, err = check_link(token)
    if err:
        abort(403)
    ok, e2 = register_download(link)
    if not ok:
        abort(403)
    f = File.query.get(link.file_id)
    return send_file(f.path, as_attachment=True, download_name=f.name)

@bp.get("/api/files")
def list_files():
    return jsonify({"files": [{"id": f.id, "name": f.name, "size": f.size,
                               "links": ShareLink.query.filter_by(file_id=f.id).count(),
                               "downloads": sum(l.downloads for l in ShareLink.query.filter_by(file_id=f.id).all())}
                              for f in File.query.all()]})

@bp.delete("/api/files/<int:fid>")
def delete_file(fid):
    f = File.query.get_or_404(fid)
    for l in ShareLink.query.filter_by(file_id=fid).all():
        db.session.delete(l)
    db.session.delete(f)
    db.session.commit()
    return jsonify({"status": "deleted"})
