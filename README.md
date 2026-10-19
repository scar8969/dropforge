<p align="center">
  <img src="docs/assets/screens/root.png" alt="dropforge running" width="900">
</p>

<h1 align="center">dropforge</h1>

<p align="center"><b>Upload a file, get a link you can expire, password and cap.</b></p>

<p align="center">
  <a href="https://github.com/scar8969/dropforge/actions/workflows/ci.yml"><img src="https://github.com/scar8969/dropforge/actions/workflows/ci.yml/badge.svg" alt="ci"></a> <a href="#quality-gates"><img src="https://img.shields.io/badge/tests-132%20passed-2ea44f" alt="tests: 132 passed"></a> <a href="#quality-gates"><img src="https://img.shields.io/badge/coverage-100.0%-brightgreen" alt="coverage: 100.0%"></a> <a href="#api"><img src="https://img.shields.io/badge/routes-9%20live-0969da" alt="routes: 9 live"></a> <a href="#requirements"><img src="https://img.shields.io/badge/python-3.11%2B-3776ab" alt="python: 3.11+"></a> <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-2ea44f" alt="license: MIT"></a>
</p>

dropforge is a self-hosted file handoff: upload over HTTP, receive a short token, and control that link with a password, an expiry and a download limit. Every download is counted, and the share page says why a link stopped working.

---

**Contents** &nbsp;·&nbsp; [Why](#why-this-exists) &nbsp;·&nbsp; [What it does](#what-it-does) &nbsp;·&nbsp; [Quickstart](#quickstart) &nbsp;·&nbsp; [Screenshots](#screenshots) &nbsp;·&nbsp; [API](#api) &nbsp;·&nbsp; [CLI](#cli) &nbsp;·&nbsp; [Configuration](#configuration) &nbsp;·&nbsp; [Measured](#measured-not-estimated) &nbsp;·&nbsp; [How a request flows](#how-a-request-flows) &nbsp;·&nbsp; [Architecture](#architecture) &nbsp;·&nbsp; [Quality gates](#quality-gates) &nbsp;·&nbsp; [Development](#development) &nbsp;·&nbsp; [Deploy](#deploy) &nbsp;·&nbsp; [Limits](#limits-stated-rather-than-hidden)

## Why this exists

Sending a file should not mean uploading it to somebody else's bucket. The hard part is not the upload — it is the lifecycle: expiry that is enforced rather than displayed, a password that is checked server-side, and a cap that actually stops the fourth download.

## What it does

| Capability | How it works |
| --- | --- |
| **Short share links** | A random token per file; GET /s/<token> is the page, GET /dl/<token> is the bytes. |
| **Password-gated shares** | A locked link answers `need_password` until the password is supplied; the download route checks it again, so the file never leaves without it. |
| **Expiry and download caps** | Checked on every request; an exhausted link returns 410 with the reason, not a silent 404. |
| **Streamed uploads** | The file is written to disk as it arrives; large files do not sit in memory. |
| **List and delete** | GET /api/files and DELETE /api/files/<id> for cleanup, plus a CLI. |

## Quickstart

```sh
git clone https://github.com/scar8969/dropforge.git
cd dropforge
python -m venv .venv && . .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
python wsgi.py                                 # http://127.0.0.1:8000
```

It is up when this answers:

```sh
curl -s http://127.0.0.1:8000/api/health
```

## Screenshots

Captured from the running service with headless Chromium at 1440×900, one image per page, committed under [`docs/assets/screens/`](docs/assets/screens/).

<table>
<tr>
<td width="50%"><img src="docs/assets/screens/files.png" alt="/files" width="100%"><br><sub><code>/files</code> &middot; 21.6 KB</sub></td>
<td width="50%"><img src="docs/assets/screens/healthz.png" alt="/healthz" width="100%"><br><sub><code>/healthz</code> &middot; 8.2 KB</sub></td>
</tr>
</table>

<table>
<tr>
<td width="50%"><img src="docs/assets/screens/livez.png" alt="/livez" width="100%"><br><sub><code>/livez</code> &middot; 7.3 KB</sub></td>
<td width="50%"><img src="docs/assets/screens/metrics.png" alt="/metrics" width="100%"><br><sub><code>/metrics</code> &middot; 16.2 KB</sub></td>
</tr>
</table>

<table>
<tr>
<td width="50%"><img src="docs/assets/screens/readyz.png" alt="/readyz" width="100%"><br><sub><code>/readyz</code> &middot; 7.7 KB</sub></td>
<td width="50%"><img src="docs/assets/screens/version.png" alt="/version" width="100%"><br><sub><code>/version</code> &middot; 26.1 KB</sub></td>
</tr>
</table>

## API

Every route below is declared in [`openapi/dropforge.yaml`](openapi/dropforge.yaml) and exercised by the live probe recorded in [`docs/EVIDENCE.md`](docs/EVIDENCE.md).

| Method | Path | What it does |
| --- | --- | --- |
| `GET` | `/api/health` | application health |
| `POST` | `/api/upload` | upload file |
| `GET` | `/s/<token>` | share page |
| `POST` | `/s/<token>` | unlock |
| `GET` | `/dl/<token>` | download |
| `GET` | `/api/files` | list |
| `DELETE` | `/api/files/<id>` | delete |

## CLI

The same operations without an HTTP client. Installed as `dropforge`, and runnable from a checkout with no install:

```sh
python -m go_file.cli --help
```

```text
usage: gofile [-h] [--base BASE] {put,ls} ...

go-file command line client

positional arguments:
  {put,ls}
    put        upload a file and create a share link
    ls         list uploaded files

options:
  -h, --help   show this help message and exit
  --base BASE  base URL of a running instance
```

## Configuration

Environment only — there is no config file. Copy `.env.example` to `.env` and edit; `APP_ENV=production` refuses to start without `SECRET_KEY`.

| Variable | Default | Meaning |
| --- | --- | --- |
| `APP_ENV` | `development` | development \| staging \| production; production enforces the secret. |
| `SECRET_KEY` | `change-me-in-production` | Session/CSRF signing key. Required when APP_ENV=production. |
| `HOST` | `0.0.0.0` | Interface the dev server binds. |
| `PORT` | `8000` | Port the dev server and the container listen on. |
| `DEBUG` | `false` | Flask debug mode. Never true in production. |
| `MAX_CONTENT_LENGTH` | `8388608` | Largest accepted request body, in bytes. |
| `DATA_DIR` | `(empty)` | Where uploaded and generated files live. |
| `INSTANCE_DIR` | `(empty)` | Where the SQLite file and instance state live. |
| `LOG_DIR` | `(empty)` | Where rotated log files are written, if file logging is on. |
| `LOG_LEVEL` | `INFO` | DEBUG \| INFO \| WARNING \| ERROR. |
| `LOG_JSON` | `true` | true emits one JSON object per line; false is human-readable. |
| `REQUEST_ID_HEADER` | `X-Request-ID` | Header echoed on every response and stamped on every log line. |
| `UPLOAD_ROOT` | `(empty)` | Directory uploads are written to; defaults under the data dir. |
| `GOFILE_URL` | `http://127.0.0.1:8000` | Base URL the CLI talks to; also accepted as --url. |
| `ANALYTICS_SALT` | `change-me-in-production` | Salt for the visitor hash. Changing it resets visitor identity. |

## Measured, not estimated

Produced on this checkout by `pytest --cov` and by booting `wsgi.py` and issuing one real GET per documented path. The commands are recorded in [`docs/EVIDENCE.md`](docs/EVIDENCE.md).

| Signal | Value |
| --- | --- |
| Tests | **132 / 132 passed** (18.5 s, exit 0) |
| Line coverage | **100.0%** — 754 of 754 statements |
| Source | 15 files / 1,599 lines |
| Test code | 14 files / 1,402 lines |
| Documented paths | 6 in the spec, 4 GET |
| Live probe | 13 GET requests to the booted app, **9 answered 200** |
| Median latency | **17.4 ms** (single uncached request, dev server) |
| Slowest / fastest | 53.9 ms `/` / 7.2 ms `/f/demo` |
| Bytes served | 15.9 KB across 13 responses |
| Screenshots | 7 captured |

## How a request flows

```text
client
  │  HTTP
  ▼
wsgi.py ──▶ go_file/app.py:get_app()
                │  reads config once (go_file/config.py)
                │  registers the `share` blueprint
                ▼
           route handler
             ├──▶ go_file/models.py        tables, via Flask-SQLAlchemy
             ├──▶ go_file/errors.py        raises typed errors → one JSON envelope
             └──▶ go_file/observability.py JSON log line + X-Request-ID
```

Every response carries `X-Request-ID`, and the matching log line is written once at the end of the request with the status and duration, so a report of "it failed" is one `grep` away from the traceback.

## Architecture

```
dropforge/
├── src/go_file/
│   ├── http.py                         383  HTTP plumbing for go_file: correlation ids, access l
│   ├── config.py                       173  Environment-driven configuration for go_file
│   ├── observability.py                169  Structured logging and request correlation for go_fi
│   ├── _app.py                         151  
│   ├── cli.py                          121  Command line client for go-file
│   ├── app.py                          119  Application factory for go_file
│   ├── errors.py                       108  Typed application errors and their HTTP mapping for 
│   ├── share/api.py                    101  
│   ├── share/storage.py                 86  
│   ├── share/links.py                   80  
│   ├── models.py                        56  
│   ├── paths.py                         52  Filesystem layout for go_file
├── openapi/dropforge.yaml                 the contract of record
├── schema/dropforge.sql                   the DDL
├── tests/                       the suite that has to stay green
├── docs/EVIDENCE.md             the recorded live route walk
├── Dockerfile                   multi-stage build
└── wsgi.py                      entry point
```

The package keeps one shape across the service: `config.py` reads the environment once, `observability.py` emits structured JSON logs carrying a request id, `errors.py` turns exceptions into a single JSON envelope, `models.py` holds the tables, and the `share/` package holds the routes.

## Quality gates

| Gate | Command | Threshold |
| --- | --- | --- |
| Suite | `pytest -q` | all green |
| Coverage | `pytest --cov` | floor in `pyproject.toml`, set below the measured value |
| Lint | `ruff check src tests` | zero findings |
| Format | `ruff format --check src tests` | zero reformats |
| Types | `mypy src` | zero errors |
| Security | `bandit -c pyproject.toml -r src` | reviewed skip list, no unreviewed finding |
| Live routes | boot `wsgi.py`, one GET per documented path | no 5xx, no undocumented guard |

CI runs the first six on Python 3.11, 3.12 and 3.13 on every push to `main`, plus a container build — [`.github/workflows/ci.yml`](.github/workflows/ci.yml).

## Development

```sh
pip install -e ".[dev]"
python -m pytest -q                      # the suite
python -m pytest --cov                   # with the coverage floor
python -m ruff check src tests           # lint
python -m ruff format --check src tests  # formatting
python -m mypy src                       # types
python -m bandit -c pyproject.toml -r src  # security
pre-commit install                       # the same checks on commit
```

Dependabot opens grouped PRs for the dev tooling weekly and for actions and the base image monthly.

## Deploy

```sh
docker build -t dropforge .
docker run --rm -p 8000:8000 --env-file .env.example dropforge
```

A `docker-compose.yml` is included for a local run with a volume for the SQLite file. The image runs as a non-root user and serves through gunicorn.

## Limits, stated rather than hidden

- Storage is local disk under the data directory; there is no S3 backend in this release.
- Download caps are counted per request, not per distinct client.

## License

MIT — see [LICENSE](LICENSE).
