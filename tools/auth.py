import argparse

from .bili_auth import login, status
from .bili_client import load_cookies


def get_cookies():
    cookies = load_cookies()
    return cookies or None


def main():
    parser = argparse.ArgumentParser(description="BiliSubNotes B站认证工具")
    parser.add_argument("--status", action="store_true", help="仅检查登录状态")
    args = parser.parse_args()
    raise SystemExit(status() if args.status else login())


if __name__ == "__main__":
    main()
