#!/usr/bin/env python3
"""
获取 B 站视频列表 (稍后再看/收藏夹)

用法:
    python tools/list.py --watch-later --browser edge --limit 10
"""

import argparse
import json
import subprocess
import os
import sys
import requests
from pathlib import Path


def export_cookies_from_browser(browser_name, output_file):
    """使用 yt-dlp 从浏览器导出 Cookie"""
    print(f"🍪 正在从 {browser_name} 导出 Cookie...")
    cmd = [
        "yt-dlp",
        "--cookies-from-browser", browser_name,
        "--cookies", str(output_file),
        "--skip-download",
        "https://www.bilibili.com",
    ]
    
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except subprocess.CalledProcessError:
        print(f"❌ 无法从 {browser_name} 读取 Cookie。请确保浏览器已关闭或未被占用。")
        return False
    except FileNotFoundError:
        print("❌ 未找到 yt-dlp")
        return False


def parse_netscape_cookies(cookie_file):
    """解析 Netscape 格式 Cookie 文件到 dict"""
    cookies = {}
    with open(cookie_file, 'r') as f:
        for line in f:
            if line.startswith('#') or not line.strip():
                continue
            parts = line.split('\t')
            if len(parts) >= 7:
                cookies[parts[5]] = parts[6].strip()
    return cookies


def get_watch_later(cookies, limit=10):
    """获取稍后再看列表"""
    url = "https://api.bilibili.com/x/v2/history/toview"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://www.bilibili.com/"
    }
    
    resp = requests.get(url, cookies=cookies, headers=headers)
    data = resp.json()
    
    if data["code"] != 0:
        print(f"❌ API 请求失败: {data.get('message')}")
        return []
    
    videos = data["data"]["list"]
    return videos[:limit]


def main():
    parser = argparse.ArgumentParser(description="获取 B 站视频列表")
    parser.add_argument("--watch-later", "-wl", action="store_true", help="获取稍后再看")
    parser.add_argument("--browser", "-b", help="从浏览器读取 Cookie (edge, chrome)")
    parser.add_argument("--limit", "-n", type=int, default=10, help="数量限制")
    
    args = parser.parse_args()
    
    cookie_file = Path(".temp_cookies.txt")
    cookies = {}
    
    # 1. 获取 Cookie
    if args.browser:
        if export_cookies_from_browser(args.browser, cookie_file):
            cookies = parse_netscape_cookies(cookie_file)
            cookie_file.unlink()
    else:
        # 尝试加载 auth.py 保存的 session
        sys.path.insert(0, str(Path(__file__).parent))
        try:
            from auth import get_cookies
            cookies = get_cookies()
            if cookies:
                print("   认证: 使用保存的 Session ✅")
        except ImportError:
            pass

    if not cookies:
        print("❌ 未获取到有效 Cookie，无法访问私有列表")
        return

    # 2. 获取列表
    if args.watch_later:
        print(f"📋 正在获取‘稍后再看’列表 (前 {args.limit} 个)...")
        videos = get_watch_later(cookies, args.limit)
        
        if not videos:
            print("   列表为空或获取失败")
            return
            
        print(f"✅ 获取到 {len(videos)} 个视频:")
        for v in videos:
            print(f"   - [{v['bvid']}] {v['title']}")
            
        # 输出 JSON 供其他工具调用
        with open("batch_list.json", "w") as f:
            json.dump(videos, f, ensure_ascii=False, indent=2)
        print("\n💾 列表已保存到 batch_list.json")

if __name__ == "__main__":
    main()
