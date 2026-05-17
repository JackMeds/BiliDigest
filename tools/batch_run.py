import argparse

from .bilisub import main as bilisub_main


def main():
    parser = argparse.ArgumentParser(description="兼容入口：批量导出稍后再看字幕")
    parser.add_argument("--limit", type=int, default=15)
    parser.add_argument("--with-summary", action="store_true")
    parser.add_argument("--fallback-summary", action="store_true")
    parser.add_argument("--refresh-list", action="store_true")
    parser.add_argument("--no-resume", action="store_true")
    parser.add_argument("--retry-failed", action="store_true")
    args = parser.parse_args()
    cmd = ["batch", "watch-later", "--limit", str(args.limit)]
    if args.with_summary:
        cmd.append("--with-summary")
    if args.fallback_summary:
        cmd.append("--fallback-summary")
    if args.refresh_list:
        cmd.append("--refresh-list")
    if args.no_resume:
        cmd.append("--no-resume")
    if args.retry_failed:
        cmd.append("--retry-failed")
    raise SystemExit(bilisub_main(cmd))

if __name__ == "__main__":
    main()
