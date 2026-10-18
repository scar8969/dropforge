"""Share-link lifecycle contract: tokens, expiry, passwords, download caps.

Links are created through the real session against the throwaway database
installed by the suite-wide conftest.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta

import pytest

from go_file.errors import BadRequest
from go_file.models import File, ShareLink, db
from go_file.share.links import check_link, create_link, make_token, register_download


def _make_file(sha="a" * 64):
    row = File(name="a.txt", size=3, sha256=sha, storage="local", path="/tmp/a.txt")
    db.session.add(row)
    db.session.commit()
    return row


def test_make_token_is_eight_alphanumeric_characters():
    token = make_token()
    assert len(token) == 8
    assert all(ch.isalnum() and ch.isascii() for ch in token)


def test_tokens_do_not_repeat():
    assert len({make_token() for _ in range(50)}) == 50


def test_create_link_without_limits_is_unbounded():
    link = create_link(_make_file().id)
    assert link.expires_at is None
    assert link.password_hash is None
    assert link.max_downloads is None
    assert link.downloads == 0


def test_create_link_honours_hours_and_days():
    file_id = _make_file().id
    hourly = create_link(file_id, "2h")
    daily = create_link(file_id, "3d")
    now = datetime.now(UTC).replace(tzinfo=None)
    assert timedelta(hours=1, minutes=59) < hourly.expires_at - now < timedelta(hours=2, minutes=1)
    assert timedelta(days=2, hours=23) < daily.expires_at - now < timedelta(days=3, minutes=1)


def test_create_link_hashes_the_password():
    link = create_link(_make_file().id, password="secret")
    assert link.password_hash == hashlib.sha256(b"secret").hexdigest()
    assert link.password_hash != "secret"


def test_create_link_rejects_an_unknown_expiry_unit():
    with pytest.raises(BadRequest, match="end in h or d"):
        create_link(_make_file().id, "5m")


def test_create_link_rejects_a_non_numeric_expiry():
    with pytest.raises(BadRequest, match="24h or 7d"):
        create_link(_make_file().id, "abch")


def test_check_link_reports_an_unknown_token():
    link, error = check_link("nope")
    assert link is None
    assert error == "not found"


def test_check_link_deletes_an_expired_link():
    link = create_link(_make_file().id)
    link.expires_at = datetime.now(UTC).replace(tzinfo=None) - timedelta(seconds=1)
    db.session.commit()
    found, error = check_link(link.token)
    assert found is None
    assert error == "expired"
    assert ShareLink.query.filter_by(token=link.token).first() is None


def test_check_link_requires_the_password():
    link = create_link(_make_file().id, password="secret")
    assert check_link(link.token) == (None, "bad password")
    found, error = check_link(link.token, "secret")
    assert found is not None
    assert error is None


def test_check_link_enforces_the_download_cap():
    link = create_link(_make_file().id, max_dl=2)
    assert link.max_downloads == 2
    link.downloads = 2
    db.session.commit()
    assert check_link(link.token) == (None, "limit exceeded")


def test_register_download_increments_the_counter():
    link = create_link(_make_file().id, max_dl=2)
    assert register_download(link) == (True, None)
    assert link.downloads == 1


def test_register_download_refuses_once_the_cap_is_reached():
    link = create_link(_make_file().id, max_dl=1)
    link.downloads = 1
    db.session.commit()
    assert register_download(link) == (False, "limit exceeded")
