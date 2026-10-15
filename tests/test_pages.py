"""Server-rendered page contract: upload, inventory, detail and share flows."""
from __future__ import annotations

import io
import os
from datetime import UTC, datetime, timedelta

from go_file.models import File, ShareLink, db


def _upload(client, content=b"page", name="page.txt", **fields):
    data = {"file": (io.BytesIO(content), name)}
    data.update(fields)
    return client.post("/upload", data=data, content_type="multipart/form-data")


def test_health_endpoint_reports_the_service(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok", "service": "go-file", "version": "0.1.0"}


def test_index_renders_the_empty_state(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "No files stored yet" in response.get_data(as_text=True)


def test_files_page_lists_an_uploaded_file(client):
    _upload(client, name="listed.txt")
    response = client.get("/files")
    assert response.status_code == 200
    assert "listed.txt" in response.get_data(as_text=True)


def test_upload_without_a_file_flashes_and_redirects(client):
    response = client.post("/upload", data={}, content_type="multipart/form-data")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/")


def test_upload_redirects_to_the_detail_page(client):
    response = _upload(client, name="detail.txt")
    assert response.status_code == 302
    assert "/f/" in response.headers["Location"]
    assert File.query.count() == 1


def test_upload_of_a_duplicate_removes_the_new_blob(client):
    first = _upload(client, content=b"same", name="first.txt")
    second = _upload(client, content=b"same", name="second.txt")
    assert first.status_code == 302 and second.status_code == 302
    assert File.query.count() == 1
    assert File.query.first().name == "first.txt"


def test_upload_tolerates_a_non_numeric_download_cap(client):
    response = _upload(client, max_downloads="many")
    assert response.status_code == 302
    assert ShareLink.query.one().max_downloads is None


def test_upload_rejects_an_unknown_expiry(client):
    response = _upload(client, expiry="5m")
    assert response.status_code == 400
    assert ShareLink.query.count() == 0


def test_file_detail_renders_and_missing_files_are_not_found(client):
    _upload(client, name="seen.txt")
    row = File.query.one()
    response = client.get(f"/f/{row.id}")
    assert response.status_code == 200
    assert "seen.txt" in response.get_data(as_text=True)
    assert client.get("/f/9999").status_code == 404


def test_add_link_creates_a_second_share_link(client):
    _upload(client)
    row = File.query.one()
    response = client.post(f"/f/{row.id}/link", data={"expiry": "1h", "password": "pw"})
    assert response.status_code == 302
    assert ShareLink.query.count() == 2


def test_delete_file_removes_row_links_and_blob(client):
    _upload(client)
    row = File.query.one()
    path = row.path
    response = client.post(f"/f/{row.id}/delete")
    assert response.status_code == 302
    assert File.query.count() == 0 and ShareLink.query.count() == 0
    assert not os.path.exists(path)


def test_share_page_offers_the_download_to_anyone(client):
    _upload(client, name="shared.txt")
    token = ShareLink.query.one().token
    response = client.get(f"/share/{token}")
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "shared.txt" in body and "Download" in body


def test_share_page_asks_for_the_password(client):
    _upload(client, password="pw")
    token = ShareLink.query.one().token
    response = client.get(f"/share/{token}")
    assert response.status_code == 200
    assert "Password required" in response.get_data(as_text=True)


def test_share_page_unlocks_with_the_right_password(client):
    _upload(client, password="pw")
    token = ShareLink.query.one().token
    response = client.post(f"/share/{token}", data={"password": "pw"})
    assert response.status_code == 200
    assert "Password required" not in response.get_data(as_text=True)


def test_share_page_rejects_the_wrong_password(client):
    _upload(client, password="pw")
    token = ShareLink.query.one().token
    response = client.post(f"/share/{token}", data={"password": "nope"})
    assert response.status_code == 200
    assert "Password required" in response.get_data(as_text=True)


def test_share_page_reports_an_unknown_token(client):
    assert client.get("/share/nope").status_code == 404


def test_share_page_reports_an_expired_token(client):
    _upload(client)
    link = ShareLink.query.one()
    link.expires_at = datetime.now(UTC).replace(tzinfo=None) - timedelta(seconds=1)
    db.session.commit()
    assert client.get(f"/share/{link.token}").status_code == 404


def test_a_relative_blob_path_is_rebased_against_the_upload_root(client):
    from go_file import _app

    row = File(name="rel.txt", size=1, sha256="c" * 64, storage="local", path="./data/rel.txt")
    db.session.add(row)
    db.session.commit()
    client.get("/")
    db.session.refresh(row)
    assert row.path == os.path.join(_app.app.config["UPLOAD_ROOT"], "rel.txt")
    assert os.path.isabs(row.path)
