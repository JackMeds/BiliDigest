import argparse
import json
import sys
import time

from . import bili_auth
from .bili_client import BiliClient, BiliError, RiskControl, dated_output_dir
from .bili_batch import DEFAULT_CACHE_TTL_SECONDS, get_watch_later_items, load_state, save_state
from .bili_library import favorite_folders, favorite_items, watch_later, write_jsonl
from .bili_subtitle import export_transcript
from .bili_summary import export_summary


DEFAULT_LIMIT = 15


def print_json(data: object) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def cmd_auth(args: argparse.Namespace) -> int:
    forwarded = [args.action]
    if args.value:
        forwarded.append(args.value)
    if args.json:
        forwarded.append("--json")
    if args.no_wait:
        forwarded.append("--no-wait")
    return bili_auth.main(forwarded)


def cmd_list(args: argparse.Namespace) -> int:
    client = BiliClient()
    out_dir = dated_output_dir()
    if args.kind == "watch-later":
        if args.no_cache:
            items = watch_later(client, args.limit)
            cache_info = {"source": "network", "cache": "disabled"}
        else:
            items, cache_info = get_watch_later_items(
                client,
                args.limit,
                cache_ttl=args.cache_ttl,
                refresh=args.refresh,
                progress=lambda message: print(message, file=sys.stderr, flush=True),
            )
        path = write_jsonl(items, "watch-later", out_dir)
        payload = {"count": len(items), "path": str(path), "cache": cache_info}
        if not args.no_items:
            payload["items"] = items
        print_json(payload)
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
    items, cache_info = get_watch_later_items(
        client,
        args.limit,
        cache_ttl=args.cache_ttl,
        refresh=args.refresh_list,
        progress=lambda message: print(message, file=sys.stderr, flush=True),
    )
    state = load_state("watch-later")
    if not args.resume:
        state = {
            "source": "watch-later",
            "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "updated_at": None,
            "total": 0,
            "completed": {},
            "failed": {},
            "skipped": {},
            "last_error": None,
        }
    state["total"] = len(items)
    state["limit"] = args.limit
    state["cache"] = cache_info
    state["output_dir"] = str(out_dir)
    progress_path = save_state("watch-later", state)

    completed = state["completed"]
    failed = state["failed"]
    skipped = state["skipped"]
    print(f"批处理开始：{len(items)} 条，输出 {out_dir}，状态 {progress_path}", file=sys.stderr, flush=True)
    for index, item in enumerate(items, 1):
        bvid = item.get("bvid")
        title = item.get("title")
        if not bvid:
            continue
        if args.resume and bvid in completed:
            skipped[bvid] = {"title": title, "reason": "completed", "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
            save_state("watch-later", state)
            print(f"[{index}/{len(items)}] 跳过已完成 {bvid} {title}", file=sys.stderr, flush=True)
            continue
        if args.resume and bvid in failed and not args.retry_failed:
            skipped[bvid] = {"title": title, "reason": "failed_before", "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
            save_state("watch-later", state)
            print(f"[{index}/{len(items)}] 跳过之前失败 {bvid} {title}", file=sys.stderr, flush=True)
            continue

        print(f"[{index}/{len(items)}] 处理 {bvid} {title}", file=sys.stderr, flush=True)
        try:
            transcript = export_transcript(client, bvid, "md", out_dir=out_dir)
            summary = None
            if args.with_summary:
                try:
                    summary = export_summary(client, bvid, out_dir=out_dir)
                except BiliError as exc:
                    summary = {"error": str(exc), "code": exc.code}
            completed[bvid] = {
                "bvid": bvid,
                "title": title,
                "status": "transcript",
                "transcript": transcript,
                "summary": summary,
                "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            }
            failed.pop(bvid, None)
        except BiliError as exc:
            summary = None
            if (args.fallback_summary or args.with_summary) and not exc.stop_batch:
                try:
                    summary = export_summary(client, bvid, out_dir=out_dir)
                except BiliError as summary_exc:
                    summary = {"error": str(summary_exc), "code": summary_exc.code}
                else:
                    completed[bvid] = {
                        "bvid": bvid,
                        "title": title,
                        "status": "summary_only",
                        "transcript_error": {"error": str(exc), "code": exc.code},
                        "summary": summary,
                        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                    }
                    failed.pop(bvid, None)
                    save_state("watch-later", state)
                    continue
            failed[bvid] = {
                "bvid": bvid,
                "title": title,
                "error": str(exc),
                "code": exc.code,
                "summary": summary,
                "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            }
            state["last_error"] = failed[bvid]
            if exc.stop_batch:
                save_state("watch-later", state)
                break
        except KeyboardInterrupt:
            state["last_error"] = {"error": "Interrupted by user", "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
            save_state("watch-later", state)
            raise
        except Exception as exc:
            failed[bvid] = {
                "bvid": bvid,
                "title": title,
                "error": f"{type(exc).__name__}: {exc}",
                "code": None,
                "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            }
            state["last_error"] = failed[bvid]
        finally:
            progress_path = save_state("watch-later", state)
    print_json(
        {
            "progress": str(progress_path),
            "output_dir": str(out_dir),
            "total": len(items),
            "completed": len(completed),
            "failed": len(failed),
            "skipped": len(skipped),
            "cache": cache_info,
        }
    )
    return 0


def build_parser(prog: str = "bilidigest") -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog=prog, description="BiliDigest 哔哩摘要笔记 CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    auth = sub.add_parser("auth", help="B站登录状态和扫码登录")
    auth.add_argument("action", choices=["status", "login", "poll", "import-browser", "session-path"])
    auth.add_argument("value", nargs="?")
    auth.add_argument("--json", action="store_true")
    auth.add_argument("--no-wait", action="store_true")
    auth.set_defaults(func=cmd_auth)

    list_parser = sub.add_parser("list", help="列出稍后再看或收藏夹")
    list_parser.add_argument("kind", choices=["watch-later", "favorites", "favorite"])
    list_parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    list_parser.add_argument("--mid", default="me")
    list_parser.add_argument("--media-id")
    list_parser.add_argument("--cache-ttl", type=int, default=DEFAULT_CACHE_TTL_SECONDS, help="稍后再看列表缓存秒数，默认 86400")
    list_parser.add_argument("--refresh", action="store_true", help="忽略稍后再看列表缓存并重新请求")
    list_parser.add_argument("--no-cache", action="store_true", help="稍后再看列表不使用本地缓存")
    list_parser.add_argument("--no-items", action="store_true", help="只输出数量和路径，不把列表全部打印到终端")
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
    batch.add_argument("--fallback-summary", action="store_true", help="无字幕或字幕导出失败时尝试导出 B站 AI 总结")
    batch.add_argument("--cache-ttl", type=int, default=DEFAULT_CACHE_TTL_SECONDS, help="稍后再看列表缓存秒数，默认 86400")
    batch.add_argument("--refresh-list", action="store_true", help="忽略稍后再看列表缓存并重新请求")
    batch.add_argument("--resume", dest="resume", action="store_true", default=True, help="从状态文件续跑，默认开启")
    batch.add_argument("--no-resume", dest="resume", action="store_false", help="忽略旧状态，从当前列表重新处理")
    batch.add_argument("--retry-failed", action="store_true", help="重新处理状态文件里之前失败的视频")
    batch.set_defaults(func=cmd_batch)

    return parser


def main(argv: list[str] | None = None, prog: str = "bilidigest") -> int:
    parser = build_parser(prog)
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
    raise SystemExit(main(prog="bilisub"))
