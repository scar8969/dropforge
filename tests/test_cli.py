"""CLI contract: argument parsing, exit codes and printed output.

HTTP commands are driven through a stubbed urlopen, so the suite never needs a
listening server.
"""
from __future__ import annotations

import io
import json
import urllib.error

import pytest

import go_file.cli as cli


class _Response:
    def __init__(self, status=200, body="{}"):
        self.status = status
        self._body = body.encode()

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False


@pytest.fixture()
def http(monkeypatch):
    seen = {
        "calls": [],
        "response": _Response(200, '{"file_id": 1, "token": "abc", "url": "/s/abc"}'),
    }

    def fake_urlopen(request, timeout=None):
        seen["calls"].append(
            {
                "url": request.full_url,
                "method": request.get_method(),
                "body": (request.data or b"").decode("utf-8", "replace"),
                "headers": {k.lower(): v for k, v in request.header_items()},
            }
        )
        outcome = seen["response"]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    monkeypatch.setattr(cli.urllib.request, "urlopen", fake_urlopen)
    return seen


@pytest.fixture()
def upload_file(tmp_path):
    path = tmp_path / "report.pdf"
    path.write_bytes(b"pdf-bytes")
    return str(path)


def test_no_subcommand_prints_help_and_exits_zero(capsys):
    assert cli.main([]) == 0
    assert "go-file command line client" in capsys.readouterr().out


def test_put_uploads_multipart_and_prints_json(capsys, http, upload_file):
    code = cli.main(["put", upload_file, "--expiry", "1d", "--password", "pw", "--limit", "3"])
    out = capsys.readouterr().out
    call = http["calls"][0]
    assert code == 0
    assert call["method"] == "POST"
    assert call["url"].endswith("/api/upload")
    assert "multipart/form-data; boundary=----gofile" in call["headers"]["content-type"]
    assert 'name="expiry"' in call["body"] and "1d" in call["body"]
    assert 'name="password"' in call["body"] and "pw" in call["body"]
    assert 'name="max_downloads"' in call["body"] and "3" in call["body"]
    assert "report.pdf" in call["body"]
    assert out.startswith("HTTP 200") and '"token": "abc"' in out


def test_put_without_options_still_sends_the_unlimited_cap(capsys, http, upload_file):
    cli.main(["put", upload_file])
    body = http["calls"][0]["body"]
    assert 'name="expiry"' not in body
    assert 'name="password"' not in body
    assert 'name="max_downloads"' in body and "0" in body


def test_put_honours_an_explicit_base_url(capsys, http, upload_file):
    cli.main(["--base", "http://elsewhere:9000/", "put", upload_file])
    assert http["calls"][0]["url"].startswith("http://elsewhere:9000/api/upload")


def test_put_reports_an_http_error(capsys, http, upload_file):
    http["response"] = urllib.error.HTTPError(
        "http://127.0.0.1:8000/api/upload",
        413,
        "Too Large",
        {},
        io.BytesIO(b'{"error": "payload_too_large"}'),
    )
    assert cli.main(["put", upload_file]) == 1
    out = capsys.readouterr().out
    assert "413" in out and "payload_too_large" in out


def test_ls_lists_files(capsys, http):
    http["response"] = _Response(
        200,
        json.dumps({"files": [{"id": 1, "name": "a.txt", "size": 10, "links": 2, "downloads": 3}]}),
    )
    assert cli.main(["ls"]) == 0
    out = capsys.readouterr().out
    assert "HTTP 200 - 1 file(s)" in out
    assert "a.txt" in out and "2" in out and "3" in out


def test_ls_on_an_empty_instance_says_so(capsys, http):
    http["response"] = _Response(200, '{"files": []}')
    assert cli.main(["ls"]) == 0
    assert "(none uploaded yet)" in capsys.readouterr().out


def test_ls_reports_an_http_error(capsys, http):
    http["response"] = urllib.error.HTTPError(
        "http://127.0.0.1:8000/api/files", 500, "Server Error", {}, io.BytesIO(b"boom")
    )
    assert cli.main(["ls"]) == 1
    assert "request failed: HTTP 500" in capsys.readouterr().out
