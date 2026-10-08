== curl ==
# curl -F "file=@report.pdf" -F "expiry=1d" -F "password=secret" http://127.0.0.1:5000/api/upload
# curl http://127.0.0.1:5000/s/8f3k2a
# curl -X POST -d '{"password":"secret"}' http://127.0.0.1:5000/s/8f3k2a
# curl -OJ http://127.0.0.1:5000/dl/8f3k2a
# CLI: gofile put ./report.pdf --expiry 1d --password secret --limit 3

== session plan ==
# Session 1: storage + links (expiry/password/limit) → tests
# Session 2: api upload/download + web templates → screenshots
# Session 3: CLI + S3 backend → README → CI/Docker/Pages → tag
