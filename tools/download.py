#!/usr/bin/env python3
"""
视频/音频下载工具 - 支持 B站/YouTube 等
"""
import sys
import argparse
import subprocess
import json
from pathlib import Path
from .utils import check_environment, get_output_dir

def create_temp_cookie_file(json_path):
    """将 JSON Session 转为 Netscape 格式供 yt-dlp 使用"""
    try:
        with open(json_path, 'r') as f:
            cookies = json.load(f)
        
        temp_path = Path("output/.temp_cookies.txt")
        temp_path.parent.mkdir(exist_ok=True)
        with open(temp_path, 'w') as f:
            f.write("# Netscape HTTP Cookie File\n")
            for k, v in cookies.items():
                f.write(f".bilibili.com\tTRUE\t/\tFALSE\t0\t{k}\t{v}\n")
        return temp_path
    except:
        return None

def download(url, output_dir, video=False, browser=None):
    """下载视频或音频"""
    # 自动识别并转换 BV 号
    if url.upper().startswith("BV"):
        url = f"https://www.bilibili.com/video/{url}"
        
    print(f"📥 正在下载: {url}")
    
    # 使用最低清晰度以优化下载速度和空间
    if video:
        format_arg = "worstvideo+worstaudio/worst"
    else:
        format_arg = "worstaudio/worst"

    output_template = str(output_dir / "%(title)s.%(ext)s")
    
    # 使用 python -m yt_dlp 方式启动，避开损坏的 Shebang 问题
    cmd = [
        sys.executable, "-m", "yt_dlp",
        url,
        "-o", output_template,
        "-f", format_arg,
        "--no-playlist",
        "--progress",
        "--ignore-errors"
    ]
    
    # 处理 Cookie
    temp_cookie = None
    if browser:
        cmd.extend(["--cookies-from-browser", browser])
    elif Path(".user_session.json").exists():
        temp_cookie = create_temp_cookie_file(".user_session.json")
        if temp_cookie:
            cmd.extend(["--cookies", str(temp_cookie)])
            print("🍪 使用本地 Session")

    try:
        process = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            text=True, 
            bufsize=1, 
            universal_newlines=True
        )
        
        filepath = None
        for line in process.stdout:
            line = line.strip()
            if line:
                print(f"   {line}")
            # 捕获文件路径
            if "Destination:" in line:
                filepath = line.split("Destination:")[-1].strip()
            elif "Merging formats into" in line:
                try:
                    filepath = line.split('"')[1]
                except:
                    pass
            elif "has already been downloaded" in line:
                try:
                    filepath = line.split("[download]")[1].split("has already")[0].strip()
                except:
                    pass

        process.wait()
        
        if process.returncode == 0:
            print("✅ 下载完成")
            if filepath:
                print(f"   文件: {filepath}")
            # 清理临时 Cookie
            if temp_cookie and temp_cookie.exists():
                temp_cookie.unlink()
            return filepath
        else:
            print("❌ 下载出错")
            stderr_output = process.stderr.read()
            if stderr_output:
                print(stderr_output)
            return None
            
    except Exception as e:
        print(f"❌ 执行异常: {e}")
        return None

if __name__ == "__main__":
    check_environment("download")
    
    parser = argparse.ArgumentParser(description="视频/音频下载工具 (yt-dlp)")
    parser.add_argument("url", help="视频链接或 BV 号")
    parser.add_argument("--video", action="store_true", help="下载视频 (默认音频)")
    parser.add_argument("--cookies-browser", "-b", help="从浏览器提取 Cookie (chrome/edge)")
    
    args = parser.parse_args()
    
    out_dir = get_output_dir()
    download(args.url, out_dir, args.video, args.cookies_browser)
