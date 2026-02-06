import sys
import time
import json
import argparse
import requests
from pathlib import Path
from .utils import check_environment

# 常量定义
SESSION_FILE = Path(".user_session.json")
QR_API_URL = "https://passport.bilibili.com/x/passport-login/web/qrcode/generate"
QR_POLL_URL = "https://passport.bilibili.com/x/passport-login/web/qrcode/poll"

class BilibiliAuth:
    def __init__(self):
        self.session_file = SESSION_FILE

    def _get_headers(self):
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://www.bilibili.com"
        }

    def check_login(self):
        """检查登录状态"""
        if not self.session_file.exists():
            return False
            
        try:
            with open(self.session_file, 'r') as f:
                cookies = json.load(f)
            
            resp = requests.get(
                "https://api.bilibili.com/x/web-interface/nav",
                cookies=cookies,
                headers=self._get_headers(),
                timeout=5
            )
            data = resp.json()
            if data['code'] == 0 and data['data']['isLogin']:
                print(f"✅ 已登录: {data['data']['uname']} (UID: {data['data']['mid']})")
                if data['data']['vipStatus'] == 1:
                    print("   会员: 大会员 ✨")
                return True
        except Exception as e:
            print(f"⚠️ 检查失败: {e}")
            
        return False

    def login_qrcode(self):
        """扫码登录"""
        try:
            # 1. 获取二维码
            resp = requests.get(QR_API_URL, headers=self._get_headers())
            data = resp.json()['data']
            qrcode_url = data['url']
            qrcode_key = data['qrcode_key']
            
            # 2. 显示二维码
            import qrcode
            qr = qrcode.QRCode()
            qr.add_data(qrcode_url)
            qr.print_ascii(invert=True)
            print("\n📱 请使用 Bilibili App 扫码登录")
            
            # 3. 轮询
            while True:
                time.sleep(2)
                resp = requests.get(
                    QR_POLL_URL,
                    params={"qrcode_key": qrcode_key},
                    headers=self._get_headers()
                )
                res = resp.json()['data']
                code = res['code']
                
                if code == 0:
                    print("✅ 登录成功!")
                    cookies = resp.cookies.get_dict()
                    with open(self.session_file, 'w') as f:
                        json.dump(cookies, f)
                    print(f"💾 Session 已保存至 {self.session_file}")
                    break
                elif code == 86038:
                    print("⌛ 二维码已失效", end="\r")
                    break
                elif code == 86090:
                    print("✅ 已扫码，请确认...", end="\r")
                else:
                    print("⏳ 等待扫码...", end="\r")
                    
        except KeyboardInterrupt:
            print("\n❌ 用户取消")

def main():
    check_environment("auth")
    
    parser = argparse.ArgumentParser(description="B站认证工具")
    parser.add_argument("--status", action="store_true", help="仅检查登录状态")
    args = parser.parse_args()
    
    auth = BilibiliAuth()
    
    if args.status:
        if not auth.check_login():
            print("❌ 未登录或 Session 无效")
            sys.exit(1)
    else:
        if auth.check_login():
            choice = input("已登录，是否重新登录? [y/N] ").strip().lower()
            if choice != 'y':
                return
        auth.login_qrcode()

if __name__ == "__main__":
    main()
