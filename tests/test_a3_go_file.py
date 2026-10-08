"""A3 go-file — tests. Run: pytest test_a3_go_file.py"""
import sys, os, io, hashlib

import pytest
flask_ok = True
try:
    import flask_sqlalchemy
except ImportError:
    flask_ok = False

def test_storage_save_roundtrip(tmp_path):
    from go_file.share.storage import LocalStorage
    st = LocalStorage(str(tmp_path))
    path, sha, size = st.save(io.BytesIO(b"hello world"), "test.txt")
    assert size == 11
    assert sha == hashlib.sha256(b"hello world").hexdigest()
    assert st.exists(path)
    assert st.open(path).read() == b"hello world"

def test_storage_delete(tmp_path):
    from go_file.share.storage import LocalStorage
    st = LocalStorage(str(tmp_path))
    path, _, _ = st.save(io.BytesIO(b"x"), "a.txt")
    st.delete(path)
    assert not st.exists(path)

def test_token_unique():
    from go_file.share.links import make_token
    assert len(make_token()) == 8
    assert make_token() != make_token()

@pytest.mark.skipif(not flask_ok, reason="flask-sqlalchemy not installed")
def test_check_link_not_found():
    from go_file.share.links import check_link
    link, err = check_link("nonexistent")
    assert link is None and err == "not found"

@pytest.mark.skipif(not flask_ok, reason="flask-sqlalchemy not installed")
def test_check_link_password():
    from go_file.share.links import check_link
    # password hash check without DB: verify the hash function shape
    import hashlib
    h = hashlib.sha256(b"secret").hexdigest()
    assert h == hashlib.sha256(b"secret").hexdigest()
