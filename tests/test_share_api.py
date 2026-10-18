"""JSON API contract for storing, sharing and downloading a file.

Files are written to the throwaway runtime directory, never var/, and downloads
are served from disk through the real storage backend.
"""

from __future__ import annotations

import io
from datetime import UTC, datetime, timedelta

from go_file.models import File, ShareLink, db
from go_file.share import api as api_module


def _upload(client, content=b"hello", name="hello.txt", **fields):
    data = {"file": (io.BytesIO(content), name)}
    data.update(fields)
    return client.post("/api/upload", data=data, content_type="multipart/form-data")


def test_upload_requires_a_file(client):
    response = client.post("/api/upload", data={}, content_type="multipart/form-data")
    assert response.status_code == 400
    assert response.get_json() == {"error": "no file"}


def test_upload_rejects_a_part_without_a_filename(client):
    response = client.post(
        "/api/upload",
        data={"file": (io.BytesIO(b"x"), "")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 400
    assert response.get_json() == {"error": "no file"}


def test_upload_stores_a_file_and_returns_a_share_url(client):
    response = _upload(client)
    body = response.get_json()
    assert response.status_code == 200
    assert body["file_id"] and body["token"]
    assert body["url"] == f"/s/{body['token']}"
    assert File.query.count() == 1
    assert ShareLink.query.count() == 1


def test_upload_deduplicates_identical_content(client):
    first = _upload(client).get_json()
    second = _upload(client).get_json()
    assert second["file_id"] == first["file_id"]
    assert second["token"] != first["token"]
    assert File.query.count() == 1
    assert ShareLink.query.count() == 2


def test_upload_rejects_an_unknown_expiry(client):
    response = _upload(client, expiry="5m")
    assert response.status_code == 400
    assert response.get_json()["error"] == "bad_request"


def test_upload_forwards_expiry_password_and_cap(client):
    token = _upload(client, expiry="1h", password="pw", max_downloads="2").get_json()["token"]
    link = ShareLink.query.filter_by(token=token).one()
    assert link.expires_at is not None
    assert link.password_hash is not None
    assert link.max_downloads == 2


def test_share_page_returns_the_download_url(client):
    token = _upload(client).get_json()["token"]
    assert client.get(f"/s/{token}").get_json() == {"url": f"/dl/{token}"}


def test_share_page_asks_for_a_password(client):
    token = _upload(client, password="pw").get_json()["token"]
    body = client.get(f"/s/{token}").get_json()
    assert body["need_password"] is True


def test_share_page_reports_an_unknown_token(client):
    assert client.get("/s/nope").status_code == 403


def test_share_page_reports_an_expired_token(client):
    token = _upload(client).get_json()["token"]
    link = ShareLink.query.filter_by(token=token).one()
    link.expires_at = datetime.now(UTC).replace(tzinfo=None) - timedelta(seconds=1)
    db.session.commit()
    assert client.get(f"/s/{token}").status_code == 410


def test_unlock_accepts_the_right_password(client):
    token = _upload(client, password="pw").get_json()["token"]
    response = client.post(f"/s/{token}", json={"password": "pw"})
    assert response.status_code == 200
    assert response.get_json() == {"url": f"/dl/{token}"}


def test_unlock_refuses_the_wrong_password(client):
    token = _upload(client, password="pw").get_json()["token"]
    assert client.post(f"/s/{token}", json={"password": "nope"}).status_code == 403


def test_download_streams_the_stored_bytes(client):
    token = _upload(client, content=b"payload").get_json()["token"]
    response = client.get(f"/dl/{token}")
    assert response.status_code == 200
    assert response.data == b"payload"
    assert "attachment" in response.headers["Content-Disposition"]


def test_download_accepts_the_password_on_the_query_string(client):
    token = _upload(client, password="pw").get_json()["token"]
    assert client.get(f"/dl/{token}").status_code == 403
    assert client.get(f"/dl/{token}?password=nope").status_code == 403
    ok = client.get(f"/dl/{token}?password=pw")
    assert ok.status_code == 200
    assert ok.data == b"hello"


def test_download_enforces_the_cap(client):
    token = _upload(client, max_downloads="1").get_json()["token"]
    assert client.get(f"/dl/{token}").status_code == 200
    assert client.get(f"/dl/{token}").status_code == 403


def test_download_refuses_when_the_quota_was_taken_between_checks(client, monkeypatch):
    token = _upload(client).get_json()["token"]
    monkeypatch.setattr(api_module, "register_download", lambda link: (False, "limit exceeded"))
    assert client.get(f"/dl/{token}").status_code == 403


def test_download_reports_a_missing_blob_row_as_not_found(client):
    body = _upload(client).get_json()
    row = db.session.get(File, body["file_id"])
    db.session.delete(row)
    db.session.commit()
    assert client.get(f"/dl/{body['token']}").status_code == 404


def test_list_files_renders_every_row(client):
    _upload(client, content=b"one", name="one.txt")
    _upload(client, content=b"two", name="two.txt")
    body = client.get("/api/files").get_json()
    assert {row["name"] for row in body["files"]} == {"one.txt", "two.txt"}


def test_delete_file_removes_the_row_and_its_links(client):
    body = _upload(client).get_json()
    assert client.delete(f"/api/files/{body['file_id']}").get_json() == {"status": "deleted"}
    assert db.session.get(File, body["file_id"]) is None
    assert ShareLink.query.count() == 0


def test_delete_file_reports_an_unknown_id(client):
    assert client.delete("/api/files/999").status_code == 404
