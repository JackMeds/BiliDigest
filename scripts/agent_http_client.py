#!/usr/bin/env python3
"""Dependency-free HTTP client for terminal agents. Secrets are read from env/files."""
import argparse
import json
import os
import pathlib
import urllib.error
import urllib.request


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("method", choices=["GET", "POST"])
    p.add_argument("path", help="API path, e.g. /v1/jobs")
    p.add_argument("--json", dest="body", default=None)
    p.add_argument("--url", default=os.getenv("BILIDIGEST_URL", "http://127.0.0.1:8765"))
    p.add_argument("--token-file", default=os.getenv("BILIDIGEST_TOKEN_FILE"))
    p.add_argument("--save", help="Save an artifact instead of printing it")
    a = p.parse_args()
    if not a.path.startswith("/") or a.path.startswith("//"):
        p.error("path must begin with a single slash")
    token = os.getenv("BILIDIGEST_API_TOKEN")
    if not token and a.token_file:
        token = pathlib.Path(a.token_file).expanduser().read_text().strip()
    if not token:
        p.error("set BILIDIGEST_API_TOKEN or --token-file")
    data = json.dumps(json.loads(a.body)).encode() if a.body else None
    req = urllib.request.Request(a.url.rstrip("/") + a.path, data=data, method=a.method, headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"})
    try:
        with urllib.request.build_opener(NoRedirect).open(req, timeout=900) as response:
            if a.save:
                path = pathlib.Path(a.save).expanduser()
                path.parent.mkdir(parents=True, exist_ok=True)
                temp = path.with_name(path.name + ".part")
                with temp.open("wb") as f:
                    while chunk := response.read(1024 * 1024):
                        f.write(chunk)
                expected = response.headers.get("Content-Length")
                if expected and temp.stat().st_size != int(expected):
                    raise RuntimeError("Incomplete artifact response")
                temp.replace(path)
                print(json.dumps({"ok": True, "path": str(path.resolve())}))
            else:
                print(response.read().decode("utf-8"))
        return 0
    except urllib.error.HTTPError as exc:
        try:
            payload = json.loads(exc.read())
        except ValueError:
            payload = {"ok": False, "error": {"code": "HTTP_ERROR", "message": f"HTTP {exc.code}"}}
        print(json.dumps(payload, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
