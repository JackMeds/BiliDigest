import argparse
import json
import sys
import time
from pathlib import Path

from . import bili_auth
from .bili_client import BiliClient, BiliError, RiskControl, dated_output_dir
from .bili_library import favorite_folders, favorite_items, watch_later, write_jsonl
from .bili_subtitle import export_transcript
from .bili_summary import export_summary


DEFAULT_LIMIT = 15


def print_json(data: object) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def cmd_auth(args: argparse.Namespace) -> int:
    forwarded = [args.action]
    if args.qrcode_key:
        forwarded.append(args.qrcode_key)
    if args.json:
        forwarded.append("--json")
    if args.no_wait:
        forwarded.append("--no-wait")
    return bili_auth.main(forwarded)


def cmd_list(args: argparse.Namespace) -> int:
    client = BiliClient()
    out_dir = dated_output_dir()
    if args.kind == "watch-later":
        items = watch_later(client, args.limit)
        path = write_jsonl(items, "watch-later", out_dir)
        print_json({"count": len(items), "path": str(path), "items": items})
        return 0
    if args.kind == "favorites":
        items = favorite_folders(client, args.mid)
        path = write_jsonl(items, "favorite-folders", out_dir)
        print_json({"count": len(items), "path": str(path), "items": items})
        return 0
    if args.kind == "favorite":
        if not args.media_id:
            raise BiliError("--media-id is required for favorite list")
        items = favorite_items(client, int(args.media_id), args.limit)
        path = write_jsonl(items, f"favorite-{args.media_id}", out_dir)
        print_json({"count": len(items), "path": str(path), "items": items})
        return 0
    raise BiliError(f"Unknown list kind: {args.kind}")


def cmd_transcript(args: argparse.Namespace) -> int:
    result = export_transcript(BiliClient(), args.video, args.format, args.lang)
    print_json(result)
    return 0


def cmd_summary(args: argparse.Namespace) -> int:
    result = export_summary(BiliClient(), args.video)
    print_json(result)
    return 0


def cmd_batch(args: argparse.Namespace) -> int:
    if args.kind != "watch-later":
        raise BiliError("Only batch watch-later is supported in this version")
    client = BiliClient()
    out_dir = dated_output_dir()
    items = watch_later(client, args.limit)
    progress = {
        "total": len(items),
        "completed": [],
        "failed": [],
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "updated_at": None,
    }
    progress_path = out_dir / "batch_progress.json"
    for item in items:
        bvid = item.get("bvid")
        try:
            transcript = export_transcript(client, bvid, "md", out_dir=out_dir)
            summary = None
            if args.with_summary:
                try:
                    summary = export_summary(client, bvid, out_dir=out_dir)
                except BiliError as exc:
                    summary = {"error": str(exc), "code": exc.code}
            progress["completed"].append({"bvid": bvid, "title": item.get("title"), "transcript": transcript, "summary": summary})
        except BiliError as exc:
            progress["failed"].append({"bvid": bvid, "title": item.get("title"), "error": str(exc), "code": exc.code})
            if exc.stop_batch:
                break
        finally:
            progress["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
            progress_path.write_text(json.dumps(progress, ensure_ascii=False, indent=2), encoding="utf-8")
    print_json({"progress": str(progress_path), **progress})
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bilisub", description="BiliSubNotes 哔哩字幕笔记 CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    auth = sub.add_parser("auth", help="B站登录状态和扫码登录")
    auth.add_argument("action", choices=["status", "login", "poll"])
    auth.add_argument("qrcode_key", nargs="?")
    auth.add_argument("--json", action="store_true")
    auth.add_argument("--no-wait", action="store_true")
    auth.set_defaults(func=cmd_auth)

    list_parser = sub.add_parser("list", help="列出稍后再看或收藏夹")
    list_parser.add_argument("kind", choices=["watch-later", "favorites", "favorite"])
    list_parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    list_parser.add_argument("--mid", default="me")
    list_parser.add_argument("--media-id")
    list_parser.set_defaults(func=cmd_list)

    transcript = sub.add_parser("transcript", help="导出 B站现成字幕")
    transcript.add_argument("video", help="BV号、B站视频URL或b23.tv短链")
    transcript.add_argument("--format", choices=["md", "srt", "json"], default="md")
    transcript.add_argument("--lang")
    transcript.set_defaults(func=cmd_transcript)

    summary = sub.add_parser("summary", help="导出 B站 AI 小助手总结")
    summary.add_argument("video")
    summary.set_defaults(func=cmd_summary)

    batch = sub.add_parser("batch", help="批量处理稍后再看")
    batch.add_argument("kind", choices=["watch-later"])
    batch.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    batch.add_argument("--with-summary", action="store_true")
    batch.set_defaults(func=cmd_batch)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except RiskControl as exc:
        print(f"已暂停: {exc}", file=sys.stderr)
        return 2
    except BiliError as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
