import argparse

from .bilisub import main as bilisub_main


def main():
    parser = argparse.ArgumentParser(description="兼容入口：批量导出稍后再看字幕")
    parser.add_argument("--limit", type=int, default=15)
    parser.add_argument("--with-summary", action="store_true")
    args = parser.parse_args()
    cmd = ["batch", "watch-later", "--limit", str(args.limit)]
    if args.with_summary:
        cmd.append("--with-summary")
    raise SystemExit(bilisub_main(cmd))

if __name__ == "__main__":
    main()
