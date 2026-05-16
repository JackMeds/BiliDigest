import argparse

from .bilisub import main as bilisub_main


def main():
    parser = argparse.ArgumentParser(description="兼容入口：获取 B站视频列表")
    parser.add_argument("--watch-later", "-wl", action="store_true", help="获取稍后再看")
    parser.add_argument("--favorites", action="store_true", help="获取收藏夹列表")
    parser.add_argument("--favorite", action="store_true", help="获取指定收藏夹内容")
    parser.add_argument("--media-id", help="收藏夹 media_id")
    parser.add_argument("--browser", "-b", help="保留参数；新版优先使用 .user_session.json")
    parser.add_argument("--limit", "-n", type=int, default=10, help="数量限制")
    args = parser.parse_args()
    if args.watch_later:
        raise SystemExit(bilisub_main(["list", "watch-later", "--limit", str(args.limit)]))
    if args.favorites:
        raise SystemExit(bilisub_main(["list", "favorites"]))
    if args.favorite:
        cmd = ["list", "favorite", "--limit", str(args.limit)]
        if args.media_id:
            cmd.extend(["--media-id", args.media_id])
        raise SystemExit(bilisub_main(cmd))
    parser.error("请指定 --watch-later、--favorites 或 --favorite")

if __name__ == "__main__":
    main()
