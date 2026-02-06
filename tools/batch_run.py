#!/usr/bin/env python3
import json
import subprocess
import os
import sys
from pathlib import Path

def main():
    # 读取列表
    if not os.path.exists("batch_list.json"):
        print("❌ 未找到 batch_list.json")
        return

    with open("batch_list.json", "r") as f:
        videos = json.load(f)

    print(f"🚀 开始批量处理 {len(videos)} 个任务...")
    print("-" * 50)

    # 获取脚本所在目录
    tools_dir = Path(__file__).parent.resolve()
    download_script = tools_dir / "download.py"
    transcribe_script = tools_dir / "transcribe.py"

    for i, video in enumerate(videos, 1):
        title = video['title']
        bvid = video['bvid']
        print(f"\n[{i}/{len(videos)}] 处理: {title} ({bvid})")
        
        # 1. 下载音频
        print("   📥 下载中...")
        cmd_dl = [
            sys.executable, 
            str(download_script), 
            bvid
        ]
        
        try:
            # 捕获输出以获取文件名
            result = subprocess.run(cmd_dl, capture_output=True, text=True, check=True)
            output_lines = result.stdout.splitlines()
            
            # 从输出中寻找文件路径
            downloaded_file = None
            for line in reversed(output_lines):
                if "   文件: " in line:
                    downloaded_file = line.split("   文件: ")[1].strip()
                    break
            
            if not downloaded_file:
                # 尝试再次查找
                print("   ⚠️ 无法解析下载路径，尝试查找最新文件...")
                downloads_dir = Path("downloads")
                files = list(downloads_dir.glob(f"*{title}*"))
                if files:
                    downloaded_file = str(files[0])
            
            if downloaded_file:
                print(f"   ✅ 下载完成: {Path(downloaded_file).name}")
                
                # 2. 转录
                print("   🎙️ 转录中 (使用 Qwen3-ASR)...")
                cmd_trans = [
                    sys.executable,
                    str(transcribe_script),
                    downloaded_file,
                    "-m", "Qwen/Qwen3-ASR-0.6B"
                ]
                subprocess.run(cmd_trans, check=True)
                
            else:
                print("   ❌ 未找到下载文件，跳过转录")
                # print(result.stderr) # Optionally print stderr
                
        except subprocess.CalledProcessError as e:
            print(f"   ❌ 处理失败: {e}")
            if e.stderr:
                print(e.stderr)

    print("\n" + "="*50)
    print("✅ 批量处理完成！")

if __name__ == "__main__":
    main()
