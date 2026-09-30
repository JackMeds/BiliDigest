import shutil
import sys
import importlib.util

from . import bili_paths

def check_command(command, install_hint):
    """检查系统命令是否存在"""
    if not shutil.which(command):
        print(f"❌ 未找到命令: {command}")
        print(f"💡 提示: {install_hint}")
        return False
    return True

def check_package(package_name, install_name=None):
    """检查 Python 包是否存在"""
    if install_name is None:
        install_name = package_name
        
    if not importlib.util.find_spec(package_name):
        print(f"❌ 未找到 Python 包: {package_name}")
        print(f"💡 提示: 请运行 'pip install {install_name}'")
        return False
    return True

def check_environment(tool_name):
    """检查工具环境"""
    print(f"🔍 [{tool_name}] 正在检查环境...")
    all_pass = True
    
    if tool_name == "download":
        if not check_package("yt_dlp", "yt-dlp"): all_pass = False
        # ffmpeg is optional but recommended
        if not shutil.which("ffmpeg"):
            print("⚠️ 未找到 FFmpeg (影响音频转换)")
            print("💡 提示: 请安装 FFmpeg 并添加到 PATH")
            
    elif tool_name == "transcribe":
        if not check_package("faster_whisper", "faster-whisper"): all_pass = False
        # transformers/torch for Qwen
        if not check_package("torch"): all_pass = False
        if not check_package("transformers"): all_pass = False

    elif tool_name == "auth":
        if not check_package("qrcode", "qrcode[pil]"): all_pass = False
        if not check_package("requests"): all_pass = False

    if not all_pass:
        print("\n❌ 环境检查未通过，请安装缺失依赖后重试。")
        sys.exit(1)
        
    print("✅ 环境检查通过")

def get_output_dir():
    """获取旧下载工具的缓存目录"""
    output_dir = bili_paths.CACHE_DIR / "downloads"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir
