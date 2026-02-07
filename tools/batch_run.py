#!/usr/bin/env python3
"""
批量处理工具 - 下载 + 转录 B站视频列表
支持后台运行，进度可追踪
"""
import json
import subprocess
import os
import sys
import time
from pathlib import Path
from datetime import datetime

def main():
    # 确保在项目根目录运行
    project_root = Path(__file__).parent.parent.resolve()
    os.chdir(project_root)
    
    # 读取列表
    list_path = project_root / "batch_list.json"
    if not list_path.exists():
        print(f"❌ 未找到 {list_path}")
        return

    with open(list_path, "r") as f:
        videos = json.load(f)

    total = len(videos)
    print(f"🚀 批量处理任务启动")
    print(f"📂 工作目录: {project_root}")
    print(f"📋 总任务数: {total}")
    print(f"⏰ 启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # Python 解释器
    python_exe = sys.executable
    output_dir = project_root / "output"
    output_dir.mkdir(exist_ok=True)

    # 进度追踪
    progress_file = project_root / "batch_progress.json"
    completed = []
    failed = []

    for i, video in enumerate(videos, 1):
        title = video.get('title', 'Unknown')
        bvid = video.get('bvid')
        if not bvid:
            print(f"\n[{i}/{total}] ⚠️ 跳过: 无效条目")
            continue
            
        print(f"\n[{i}/{total}] 🎬 {title}")
        print(f"         BV: {bvid}")
        
        # 1. 下载
        print("   📥 下载中...")
        cmd_dl = [python_exe, "-m", "tools.download", bvid]
        
        try:
            result = subprocess.run(cmd_dl, capture_output=True, text=True, timeout=300)
            
            # 查找下载的文件
            downloaded_file = None
            
            # 方法1: 从输出解析
            for line in reversed(result.stdout.splitlines()):
                if "文件:" in line:
                    downloaded_file = line.split("文件:")[-1].strip()
                    break
                if "Destination:" in line:
                    downloaded_file = line.split("Destination:")[-1].strip()
                    break
            
            # 方法2: 扫描目录找最新文件
            if not downloaded_file:
                audio_files = list(output_dir.glob("*.m4a")) + list(output_dir.glob("*.mp3")) + list(output_dir.glob("*.webm"))
                if audio_files:
                    # 找最新的
                    audio_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                    downloaded_file = str(audio_files[0])
            
            if downloaded_file and Path(downloaded_file).exists():
                print(f"   ✅ 下载完成: {Path(downloaded_file).name}")
                
                # 2. 转录
                print("   🎙️ 转录中 (Qwen3-ASR + CUDA)...")
                cmd_trans = [
                    python_exe, "-m", "tools.transcribe",
                    downloaded_file,
                    "-m", "Qwen/Qwen3-ASR-0.6B"
                ]
                trans_result = subprocess.run(cmd_trans, capture_output=True, text=True, timeout=600)
                
                if trans_result.returncode == 0:
                    print(f"   🎉 转录完成!")
                    completed.append({"bvid": bvid, "title": title, "file": downloaded_file})
                else:
                    print(f"   ⚠️ 转录失败")
                    if trans_result.stderr:
                        print(f"   {trans_result.stderr[:200]}")
                    failed.append({"bvid": bvid, "title": title, "error": "transcribe_failed"})
            else:
                print(f"   ❌ 下载失败或文件未找到")
                if result.stderr:
                    print(f"   {result.stderr[:200]}")
                failed.append({"bvid": bvid, "title": title, "error": "download_failed"})
                
        except subprocess.TimeoutExpired:
            print(f"   ⏰ 超时")
            failed.append({"bvid": bvid, "title": title, "error": "timeout"})
        except Exception as e:
            print(f"   💥 异常: {str(e)}")
            failed.append({"bvid": bvid, "title": title, "error": str(e)})
        
        # 保存进度
        with open(progress_file, "w") as f:
            json.dump({
                "total": total,
                "completed": len(completed),
                "failed": len(failed),
                "current": i,
                "last_update": datetime.now().isoformat(),
                "completed_list": completed,
                "failed_list": failed
            }, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 60)
    print(f"✅ 批量处理完成!")
    print(f"   成功: {len(completed)}/{total}")
    print(f"   失败: {len(failed)}/{total}")
    print(f"   进度文件: {progress_file}")

if __name__ == "__main__":
    main()
