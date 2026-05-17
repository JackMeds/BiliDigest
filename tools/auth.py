import argparse

from .bili_auth import login, status
from .bili_client import load_cookies


def get_cookies():
    cookies = load_cookies()
    return cookies or None


def main():
    parser = argparse.ArgumentParser(description="BiliDigest B站认证工具")
    parser.add_argument("--status", action="store_true", help="仅检查登录状态")
    parser.add_argument("--json", action="store_true", help="输出机器可读 JSON")
    parser.add_argument("--no-wait", action="store_true", help="只生成二维码，不阻塞等待扫码")
    args = parser.parse_args()
    raise SystemExit(status(args.json) if args.status else login(args.json, args.no_wait))


if __name__ == "__main__":
    main()
