import argparse
import sys
import time
from pathlib import Path

import qrcode
import requests

from .bili_client import BiliClient, LoginRequired, OUTPUT_DIR, save_cookies


QR_API_URL = "https://passport.bilibili.com/x/passport-login/web/qrcode/generate"
QR_POLL_URL = "https://passport.bilibili.com/x/passport-login/web/qrcode/poll"


def status() -> int:
    try:
        data = BiliClient(delay=0).login_status()
    except LoginRequired as exc:
        print(f"未登录: {exc}")
        return 1
    print(f"已登录: {data.get('uname')} (UID: {data.get('mid')})")
    if data.get("vipStatus") == 1:
        print("会员: 大会员")
    return 0


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


def login() -> int:
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

    print("请使用 Bilibili App 扫码登录")
    print(f"登录 URL: {qrcode_url}")
    print(f"二维码图片: {img_path}")
    _print_qr_ascii(qr)
    print("状态: 等待扫码")

    while True:
        time.sleep(2)
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
            print("状态: 登录成功，Session 已保存到 .user_session.json")
            return 0
        if code == 86038:
            print("状态: 二维码已失效")
            return 1
        if code == 86090:
            print("状态: 已扫码，请在手机端确认")
        else:
            print("状态: 等待扫码")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="BiliSubNotes B站登录工具")
    parser.add_argument("action", nargs="?", choices=["status", "login"], default="login")
    args = parser.parse_args(argv)
    if args.action == "status":
        return status()
    return login()


if __name__ == "__main__":
    raise SystemExit(main())
