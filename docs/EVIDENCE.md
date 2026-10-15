# Evidence

Every claim below comes from a command that was actually run against this
exact checkout. Nothing here is inferred from the source alone.

## Commands

```sh
# from the project directory, with _tools and _tools/_vendor on PYTHONPATH
python -m pytest -q -p hosttmp_proj tests/
python -m compileall -q src
```

## Recorded results

| check | result |
| --- | --- |
| compileall | exit 0 |
| mypy | Success: no issues found in 15 source files |
| pyflakes | 0 findings |
| pytest | 131 passed in 15.95s |
| pytest_exit_code | 0 |
| recorded_at | 2026-10-15 |
| routes_guard | 2 |
| routes_ok | 11 |
| routes_probed | 13 |

## HTTP surface

One real GET per rule in the assembled URL map, through Flask's test
client. `ok` includes 404 on a templated path: an empty database has
no such resource, and 404 is the honest answer for that.

| method | path | rule | status | bytes | note |
| --- | --- | --- | --- | --- | --- |
| GET | `/` | `/` | 200 | 5703 | ok |
| GET | `/api/files` | `/api/files` | 200 | 13 | ok |
| GET | `/api/health` | `/api/health` | 200 | 54 | ok |
| GET | `/dl/demo` | `/dl/<token>` | 403 | 157 | guard |
| GET | `/f/demo` | `/f/<int:fid>` | 404 | 207 | ok |
| GET | `/files` | `/files` | 200 | 4417 | ok |
| GET | `/healthz` | `/healthz` | 200 | 54 | ok |
| GET | `/livez` | `/livez` | 200 | 19 | ok |
| GET | `/metrics` | `/metrics` | 200 | 354 | ok |
| GET | `/readyz` | `/readyz` | 200 | 31 | ok |
| GET | `/s/demo` | `/s/<token>` | 403 | 157 | guard |
| GET | `/share/demo` | `/share/<token>` | 404 | 4179 | ok |
| GET | `/version` | `/version` | 200 | 863 | ok |

## Operational endpoints

`/healthz` answered **200**:

```
{"service":"go_file","status":"ok","version":"0.1.0"}
```

`/livez` answered **200**:

```
{"status":"alive"}
```

`/readyz` answered **200**:

```
{"checks":[],"status":"ready"}
```

`/metrics` answered **200**:

```
# TYPE http_requests_total counter
http_requests_total{method="GET",status="200"} 4
# TYPE http_request_duration_seconds_sum counter
http_request_duration_seconds_sum{method="GET"} 0.0406652
http_requests_total{method="GET",status="403"} 1
http_requests_total{method="GET",status="404"} 1
# TYPE process_uptime_seconds gauge
process_uptime_seconds 0.920
```

`/version` answered **200**:

```
{"config":{"app_name":"go_file","data_dir":"C:\\Users\\priya\\Desktop\\project-skeletons\\projects\\a3_go_file\\var","database_configured":false,"debug":false,"env":"development","host":"0.0.0.0","legacy_env_present":[],"log_json":true,"log_level":"INFO","port":8000,"secret_key_configured":false},"paths":{"data_dir":"C:\\Users\\priya\\Desktop\\project-skeletons\\projects\\a3_go_file\\var","instanc
```

## Headers observed on /healthz

| header | value |
| --- | --- |
| X-Request-ID | 6dcc82d5ef3842ad935c949b4b9c025e |
| X-Content-Type-Options | nosniff |
| X-Frame-Options | DENY |
| Referrer-Policy | no-referrer |
| Cross-Origin-Opener-Policy | same-origin |
| Permissions-Policy | geolocation=(), microphone=(), camera=() |
| Content-Type | application/json |

## Static analysis

`python -m pyflakes src tests conftest.py wsgi.py` reported **0 finding(s)**:

```
(no output)
```

`python -m mypy --config-file mypy.ini src` said:

```
Success: no issues found in 15 source files
```

`ruff`, `bandit` and `pip-audit` are configured in this project but are absent from this host and cannot be installed without network access, so no result for them is recorded either way.

## What this file does not claim

- No screenshot anywhere in this repository. The host that produced this file cannot run a headless browser: Chrome in --headless=new exits 21 on an OS access denial, Edge dies at the same point in mojo, and the Playwright bundle fails at launch() with WinError 5 even though its chrome-headless-shell.exe is present. The HTTP surface is evidenced with recorded status codes and bodies instead, and no placeholder image was added to take a screenshot's place.
- No network access: the suite is hermetic and contacts no remote host.
- No container run: the Dockerfile is reviewed, not executed, because no
  container runtime is reachable from this host.
