"""Command line client for go-file.

    python cli.py --help
    python cli.py put ./report.pdf --expiry 1d --password secret --limit 3
    python cli.py ls

Talks to a running instance (see README: python wsgi.py).
"""
import argparse
import json
import os
import urllib.error
import urllib.parse
import urllib.request

DEFAULT_BASE = os.environ.get("GOFILE_URL", "http://127.0.0.1:8000")

def _call(method, path, data=None, headers=None, base=None):
    req = urllib.request.Request((base or DEFAULT_BASE).rstrip("/") + path,
                                 data=data, method=method, headers=headers or {})
    with urllib.request.urlopen(req) as r:
        return r.status, r.read()

def cmd_put(args):
    boundary = "----gofile"
    with open(args.path, "rb") as f:
        data = f.read()
    fields = []
    for name, value in (("expiry", args.expiry), ("password", args.password),
                        ("max_downloads", str(args.limit or 0))):
        if value:
            fields.append(
                f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode()
            )
    body = (b"".join(fields)
            + (f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; "
               f"filename=\"{os.path.basename(args.path)}\"\r\n"
               "Content-Type: application/octet-stream\r\n\r\n").encode()
            + data + f"\r\n--{boundary}--\r\n".encode())
    try:
        status, out = _call("POST", "/api/upload", body,
                            {"Content-Type": f"multipart/form-data; boundary={boundary}"}, args.base)
    except urllib.error.HTTPError as exc:
        print("upload failed: HTTP %s %s" % (exc.code, exc.read().decode("utf-8", "replace")))
        return 1
    print("HTTP %s" % status)
    print(json.dumps(json.loads(out.decode()), indent=2))
    return 0

def cmd_ls(args):
    try:
        status, out = _call("GET", "/api/files", base=args.base)
    except urllib.error.HTTPError as exc:
        print("request failed: HTTP %s %s" % (exc.code, exc.read().decode("utf-8", "replace")))
        return 1
    files = json.loads(out.decode()).get("files", [])
    print("HTTP %s - %d file(s)" % (status, len(files)))
    if not files:
        print("(none uploaded yet)")
        return 0
    print("%-6s %-32s %10s %6s %10s" % ("id", "name", "size", "links", "downloads"))
    for f in files:
        print("%-6s %-32s %10s %6s %10s" % (f["id"], f["name"][:32], f["size"], f["links"], f["downloads"]))
    return 0

def main(argv=None):
    p = argparse.ArgumentParser(prog="gofile", description="go-file command line client")
    p.add_argument("--base", default=DEFAULT_BASE, help="base URL of a running instance")
    sub = p.add_subparsers(dest="cmd")

    put = sub.add_parser("put", help="upload a file and create a share link")
    put.add_argument("path")
    put.add_argument("--expiry", default="", help="e.g. 1d, 7d, 24h")
    put.add_argument("--password", default="")
    put.add_argument("--limit", type=int, default=0, help="max downloads (0 = unlimited)")
    put.set_defaults(func=cmd_put)

    ls = sub.add_parser("ls", help="list uploaded files")
    ls.set_defaults(func=cmd_ls)

    args = p.parse_args(argv)
    if getattr(args, "func", None) is None:
        p.print_help()
        return 0
    return args.func(args)
