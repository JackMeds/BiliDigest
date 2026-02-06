import sys
import argparse
import subprocess
import json
from pathlib import Path
from .utils import check_environment, get_output_dir

def get_cookies_arg(browser=None):
    """获取 Cookies 参数"""
    if browser:
        print(f"🍪 使用浏览器 Cookie: {browser}")
        return ["--cookies-from-browser", browser]
    
    # 尝试加载本地 Session
    session_file = Path(".user_session.json")
    if session_file.exists():
        # yt-dlp 需要 Netscape 格式，这里如果不方便转换，可以尝试让 yt-dlp 直接读取(不支持JSON)
        # 变通：如果 browser 未指定，且有 session，我们手动构造一个 cookie file 给 yt-dlp
        # 或者提示用户扫码。
        # 这里简化：如果不指定浏览器，且有session，尝试用 --cookies 传递临时文件
        pass
    
    return []

def create_temp_cookie_file(json_path):
    """(辅助) 将 JSON Session 转为 Netscape 格式供 yt-dlp 使用"""
    try:
        with open(json_path, 'r') as f:
            cookies = json.load(f)
        
        temp_path = Path("output/.temp_cookies.txt")
        with open(temp_path, 'w') as f:
            f.write("# Netscape HTTP Cookie File\n")
            for k, v in cookies.items():
                f.write(f".bilibili.com\tTRUE\t/\tFALSE\t0\t{k}\t{v}\n")
        return temp_path
    except:
        return None

def download(url, output_dir, video=False, quality="1080", browser=None):
    """下载视频或音频"""
    print(f"📥 正在下载: {url}")
    
    # 构建 yt-dlp 命令
    # 默认下载音频 (m4a/mp3)
    if video:
        format_arg = f"bestvideo[height<={quality}]+bestaudio/best[height<={quality}]"
    else:
        format_arg = "bestaudio/best"

    output_template = str(output_dir / "%(title)s.%(ext)s")
    
    cmd = [
        "yt-dlp",
        url,
        "-o", output_template,
        "-f", format_arg,
        "--no-playlist",
        "--quiet",
        "--progress",
        "--ignore-errors"  # 即使有错误也继续
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
            print(f"   {line.strip()}")
            if "Destination" in line and not filepath:
                # 尝试抓取文件名 [download] Destination: output/foo.mp3
                parts = line.split("Destination: ")
                if len(parts) > 1:
                    filepath = parts[1].strip()
            # yt-dlp 有时只显示 Merging formats into "..."
            if "Merging formats into" in line:
                filepath = line.split('"')[1]
            if "has already been downloaded" in line:
                 filepath = line.split(": ")[1].strip()

        process.wait()
        
        if process.returncode == 0:
            print("✅ 下载完成")
            # 清理
            if temp_cookie and temp_cookie.exists():
                temp_cookie.unlink()
            return filepath
        else:
            print("❌ 下载出错")
            print(process.stderr.read())
            return None
            
    except Exception as e:
        print(f"❌ 执行异常: {e}")
        return None

if __name__ == "__main__":
    check_environment("download")
    
    parser = argparse.ArgumentParser(description="Universal Video Downloader (yt-dlp)")
    parser.add_argument("url", help="视频链接或 BV 号")
    parser.add_argument("--video", action="store_true", help="下载视频 (默认音频)")
    parser.add_argument("--quality", "-q", default="1080", help="视频质量 (1080/4k)")
    parser.add_argument("--cookies-browser", "-b", help="从浏览器提取 Cookie (chrome/edge)")
    
    args = parser.parse_args()
    
    out_dir = get_output_dir()
    download(args.url, out_dir, args.video, args.quality, args.cookies_browser)
