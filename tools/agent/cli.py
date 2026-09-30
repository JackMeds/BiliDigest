import argparse
import json
import os
import sys
from pathlib import Path

from .store import AgentError


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise AgentError("INVALID_ARGUMENT", message)


def parser():
    p = Parser(prog="bili", description="BiliDigest agent tools: JSON CLI and authenticated HTTP API")
    p.add_argument("--data-dir", help="Override private state directory")
    p.add_argument("--output-dir", help="Override collection output directory")
    sub = p.add_subparsers(dest="command", required=True, parser_class=Parser)
    sub.add_parser("doctor", help="Inspect dependencies and local configuration")
    config = sub.add_parser("configure", help="Select an existing local Whisper model")
    config.add_argument("--whisper-model", required=True)
    a = sub.add_parser("auth", help="Login without exposing cookies")
    a.add_argument("action", choices=["status", "import-bilitools", "login", "poll"])
    a.add_argument("value", nargs="?", help="BiliTools database path or QR polling key")
    d = sub.add_parser("discover", help="Save a complete resource list snapshot")
    d.add_argument("source")
    d.add_argument("--limit", type=int, default=1000)
    s = sub.add_parser("snapshot", help="Read paginated snapshot items")
    s.add_argument("id")
    s.add_argument("--offset", type=int, default=0)
    s.add_argument("--limit", type=int, default=100)
    p2 = sub.add_parser("plan", help="Select videos and processing policy")
    p2.add_argument("snapshot_id")
    p2.add_argument("--select", action="append", default=[], metavar="BV")
    p2.add_argument("--exclude", action="append", default=[], metavar="BV")
    p2.add_argument("--keyword", action="append", default=[])
    p2.add_argument("--mode", choices=["audio-preferred", "audio", "video"], default="audio-preferred")
    p2.add_argument("--asr", choices=["none", "whisper-cpp"], default="none")
    p2.add_argument("--language", default="auto")
    p2.add_argument("--summarize", action="store_true")
    p2.add_argument("--allow-partial", action="store_true")
    start = sub.add_parser("start", help="Start a plan; returns a persistent job ID")
    start.add_argument("plan_id")
    start.add_argument("--key", help="Idempotency key for repeat-safe submission")
    start.add_argument("--foreground", action="store_true")
    sub.add_parser("jobs", help="List recent jobs")
    for name in ["status", "cancel", "resume", "export", "_worker"]:
        cmd = sub.add_parser(name)
        cmd.add_argument("id")
        if name == "resume":
            cmd.add_argument("--foreground", action="store_true")
        if name == "export":
            cmd.add_argument("--include-media", action="store_true")
    serve = sub.add_parser("serve", help="Serve the same operations over authenticated HTTP")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8765)
    serve.add_argument("--token-file")
    serve.add_argument("--allow-remote", action="store_true", help="Allow a non-loopback bind; deploy behind HTTPS")
    return p


def dispatch(args):
    if args.data_dir:
        os.environ["BILIDIGEST_DATA_DIR"] = str(Path(args.data_dir).expanduser().resolve())
    if args.output_dir:
        os.environ["BILIDIGEST_OUTPUT_DIR"] = str(Path(args.output_dir).expanduser().resolve())
    from .store import Store
    from .service import Service
    service = Service(Store(args.data_dir, args.output_dir))
    c = args.command
    if c == "doctor":
        return service.doctor()
    if c == "configure":
        return service.configure(args.whisper_model)
    if c == "auth":
        return service.auth(args.action, args.value)
    if c == "discover":
        return service.discover(args.source, args.limit)
    if c == "snapshot":
        return service.snapshot(args.id, args.offset, args.limit)
    if c == "plan":
        return service.plan(args.snapshot_id, select=args.select, exclude=args.exclude, keywords=args.keyword, mode=args.mode, asr=args.asr, language=args.language, summarize=args.summarize, allow_partial=args.allow_partial)
    if c == "start":
        return service.start(args.plan_id, idempotency_key=args.key, background=not args.foreground)
    if c == "jobs":
        return service.store.jobs()
    if c == "status":
        return service.status(args.id)
    if c == "cancel":
        return service.store.cancel(args.id)
    if c == "resume":
        return service.resume(args.id, background=not args.foreground)
    if c == "export":
        return service.export(args.id, include_media=args.include_media)
    if c == "_worker":
        service.run(args.id)
        return service.status(args.id)
    if c == "serve":
        from .http import serve
        serve(service.store, args.host, args.port, args.token_file, args.allow_remote)
        return {"status": "stopped"}
    raise AgentError("INVALID_ARGUMENT", "Unknown command")


def main(argv=None):
    try:
        result = dispatch(parser().parse_args(argv))
        print(json.dumps({"ok": True, "data": result}, ensure_ascii=False))
        return 0
    except Exception as exc:
        from .service import error_payload
        error = error_payload(exc)
        print(json.dumps({"ok": False, "error": error}, ensure_ascii=False))
        return 2 if error["code"] in ("AUTH_REQUIRED", "RISK_BLOCKED") else 1


if __name__ == "__main__":
    raise SystemExit(main())
