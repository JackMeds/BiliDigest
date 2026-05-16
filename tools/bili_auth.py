import argparse
import json
import sys
import time
from pathlib import Path

import qrcode
import requests

from .bili_client import BiliClient, LoginRequired, OUTPUT_DIR, save_cookies


QR_API_URL = "https://passport.bilibili.com/x/passport-login/web/qrcode/generate"
QR_POLL_URL = "https://passport.bilibili.com/x/passport-login/web/qrcode/poll"


def status_payload() -> dict[str, object]:
    try:
        data = BiliClient(delay=0).login_status()
    except LoginRequired as exc:
        return {"status": "not_logged_in", "message": str(exc)}
    return {
        "status": "logged_in",
        "uname": data.get("uname"),
        "mid": data.get("mid"),
        "vip": data.get("vipStatus") == 1,
    }


def print_payload(payload: dict[str, object], as_json: bool = False) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    if payload["status"] == "logged_in":
        print(f"已登录: {payload.get('uname')} (UID: {payload.get('mid')})")
        if payload.get("vip"):
            print("会员: 大会员")
    elif payload["status"] == "login_required":
        print("请使用 Bilibili App 扫码登录")
        print(f"登录 URL: {payload['login_url']}")
        print(f"二维码图片: {payload['qr_image']}")
    else:
        print(f"未登录: {payload.get('message')}")


def status(as_json: bool = False) -> int:
    payload = status_payload()
    print_payload(payload, as_json)
    return 0 if payload["status"] == "logged_in" else 1


def _print_qr_ascii(qr: qrcode.QRCode) -> None:
    matrix = qr.get_matrix()
    border_line = "  " + "██" * (len(matrix[0]) + 2)
    print(border_line)
    for row in matrix:
        line = "  ██"
        line += "".join("  " if cell else "██" for cell in row)
        line += "██"
        print(line)
    print(border_line)


def create_login_request() -> dict[str, object]:
    resp = requests.get(QR_API_URL, headers=BiliClient(delay=0).session.headers, timeout=15)
    resp.raise_for_status()
    data = resp.json()["data"]
    qrcode_url = data["url"]
    qrcode_key = data["qrcode_key"]

    qr = qrcode.QRCode(border=1)
    qr.add_data(qrcode_url)
    qr.make(fit=True)

    OUTPUT_DIR.mkdir(exist_ok=True)
    img_path = OUTPUT_DIR / "login_qr.png"
    qr.make_image(fill_color="black", back_color="white").save(img_path)

    return {
        "status": "login_required",
        "message": "请使用 Bilibili App 扫码登录",
        "login_url": qrcode_url,
        "qrcode_key": qrcode_key,
        "qr_image": str(img_path),
        "poll_command": f"python -m tools.bilisub auth poll {qrcode_key}",
    }


def poll_once(qrcode_key: str) -> dict[str, object]:
    poll = requests.get(
        QR_POLL_URL,
        params={"qrcode_key": qrcode_key},
        headers=BiliClient(delay=0).session.headers,
        timeout=15,
    )
    poll.raise_for_status()
    body = poll.json()
    result = body["data"]
    code = result["code"]
    if code == 0:
        cookies = poll.cookies.get_dict()
        if result.get("url") and "refresh_token=" in result["url"]:
            refresh = result["url"].split("refresh_token=", 1)[1].split("&", 1)[0]
            cookies["refresh_token"] = refresh
        save_cookies(cookies)
        return {"status": "logged_in", "code": code, "message": "登录成功，Session 已保存到 .user_session.json"}
    if code == 86038:
        return {"status": "expired", "code": code, "message": "二维码已失效"}
    if code == 86090:
        return {"status": "scanned", "code": code, "message": "已扫码，请在手机端确认"}
    return {"status": "pending", "code": code, "message": "等待扫码"}


def poll(qrcode_key: str, as_json: bool = False) -> int:
    payload = poll_once(qrcode_key)
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"状态: {payload['message']}")
    return 0 if payload["status"] == "logged_in" else 1


def login(as_json: bool = False, no_wait: bool = False) -> int:
    payload = create_login_request()
    print_payload(payload, as_json)
    if not as_json:
        qr = qrcode.QRCode(border=1)
        qr.add_data(str(payload["login_url"]))
        qr.make(fit=True)
        _print_qr_ascii(qr)
    if no_wait:
        return 0

    while True:
        time.sleep(2)
        current = poll_once(str(payload["qrcode_key"]))
        if current["status"] == "logged_in":
            print_payload(current, as_json)
            return 0
        if current["status"] == "expired":
            print_payload(current, as_json)
            return 1
        print_payload(current, as_json)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="BiliSubNotes B站登录工具")
    parser.add_argument("action", nargs="?", choices=["status", "login", "poll"], default="login")
    parser.add_argument("qrcode_key", nargs="?")
    parser.add_argument("--json", action="store_true", help="输出机器可读 JSON")
    parser.add_argument("--no-wait", action="store_true", help="只生成二维码，不阻塞等待扫码")
    args = parser.parse_args(argv)
    if args.action == "status":
        return status(args.json)
    if args.action == "poll":
        if not args.qrcode_key:
            parser.error("auth poll requires qrcode_key")
        return poll(args.qrcode_key, args.json)
    return login(args.json, args.no_wait)


if __name__ == "__main__":
    raise SystemExit(main())
