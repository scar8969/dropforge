"""Storage backend contract: streaming, best-effort delete, S3 shim.

boto3 is a declared dependency that is not installed on this host, so the S3
backend is driven through a fake module injected into sys.modules; no test
opens a socket.
"""

from __future__ import annotations

import hashlib
import io
import sys

import pytest

from go_file.share.storage import LocalStorage, S3Storage, StorageBackend


def test_storage_backend_is_abstract():
    backend = StorageBackend()
    with pytest.raises(NotImplementedError):
        backend.save(io.BytesIO(b""), "x")
    with pytest.raises(NotImplementedError):
        backend.open("x")
    with pytest.raises(NotImplementedError):
        backend.delete("x")
    with pytest.raises(NotImplementedError):
        backend.exists("x")


def test_local_storage_streams_a_blob_and_reads_it_back(tmp_path):
    storage = LocalStorage(str(tmp_path))
    path, sha, size = storage.save(io.BytesIO(b"payload"), "report.pdf")
    assert path.startswith(str(tmp_path))
    assert path.endswith("_report.pdf")
    assert sha == hashlib.sha256(b"payload").hexdigest()
    assert size == 7
    assert storage.exists(path) is True
    assert storage.open(path).read() == b"payload"


def test_local_storage_delete_is_best_effort(tmp_path):
    storage = LocalStorage(str(tmp_path))
    path, _sha, _size = storage.save(io.BytesIO(b"x"), "x")
    storage.delete(path)
    assert storage.exists(path) is False
    storage.delete(path)


class _Body:
    def __init__(self, data):
        self._data = data

    def read(self):
        return self._data


class _FakeS3:
    def __init__(self):
        self.calls = []

    def put_object(self, **kwargs):
        self.calls.append(("put", kwargs))

    def get_object(self, **kwargs):
        self.calls.append(("get", kwargs))
        return {"Body": _Body(b"remote")}

    def delete_object(self, **kwargs):
        self.calls.append(("delete", kwargs))

    def head_object(self, **kwargs):
        self.calls.append(("head", kwargs))
        if kwargs["Key"] == "missing":
            raise OSError("NoSuchKey")


class _FakeBoto3:
    def __init__(self, client):
        self._client = client

    def client(self, name):
        assert name == "s3"
        return self._client


@pytest.fixture()
def fake_s3(monkeypatch):
    client = _FakeS3()
    monkeypatch.setitem(sys.modules, "boto3", _FakeBoto3(client))
    return client


def test_s3_storage_puts_the_bytes_and_returns_the_key(fake_s3):
    storage = S3Storage("bucket")
    key, sha, size = storage.save(io.BytesIO(b"remote"), "photo.jpg")
    assert key.endswith("_photo.jpg")
    assert sha == hashlib.sha256(b"remote").hexdigest()
    assert size == 6
    kind, kwargs = fake_s3.calls[0]
    assert kind == "put"
    assert kwargs["Bucket"] == "bucket"
    assert kwargs["Body"] == b"remote"


def test_s3_storage_reads_a_stream(fake_s3):
    storage = S3Storage("bucket")
    assert storage.open("key").read() == b"remote"


def test_s3_storage_deletes_and_checks_existence(fake_s3):
    storage = S3Storage("bucket")
    storage.delete("key")
    assert fake_s3.calls[-1][0] == "delete"
    assert storage.exists("present") is True
    assert storage.exists("missing") is False
