import os
import sys
import argparse
import subprocess
import requests
import zipfile
import shutil
from pathlib import Path
import re

REPO_OWNER = "JackMeds"
REPO_NAME = "Video-Skill-Transcriber"
API_URL = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/releases/latest"

def get_current_version():
    """Read version from pyproject.toml"""
    try:
        with open("pyproject.toml", "r") as f:
            content = f.read()
            match = re.search(r'version\s*=\s*["\']([^"\']+)["\']', content)
            if match:
                return f"v{match.group(1)}"
    except: pass
    return "v0.0.0"

def update_via_git():
    print("🔄 Updating via Git Pull...")
    try:
        res = subprocess.run(["git", "pull"], capture_output=True, text=True)
        if res.returncode == 0:
            print(res.stdout)
            print("✅ Successfully updated via Git!")
        else:
            print(f"❌ Git Pull Failed: {res.stderr}")
    except Exception as e:
        print(f"❌ Git Error: {e}")

def update_via_zip():
    print("🔄 Checking for updates via GitHub Release...")
    try:
        current_ver = get_current_version()
        print(f"   Current Version: {current_ver}")
        
        # 1. Fetch Latest Release Info
        resp = requests.get(API_URL)
        if resp.status_code != 200:
            print(f"❌ API Error: {resp.status_code}")
            return
            
        data = resp.json()
        latest_tag = data.get("tag_name", "v0.0.0")
        download_url = data.get("zipball_url") # Use zipball (source) or verify assets?
        
        # Look for our custom zip asset first
        assets = data.get("assets", [])
        zip_asset = next((a for a in assets if a["name"].endswith(".zip")), None)
        if zip_asset:
            download_url = zip_asset["browser_download_url"]
        
        print(f"   Latest Version: {latest_tag}")
        
        if latest_tag == current_ver:
            print("✅ You are already on the latest version.")
            return

        # 2. Download
        print(f"⬇️ Downloading update from {latest_tag}...")
        save_path = "update.zip"
        with requests.get(download_url, stream=True) as r:
            with open(save_path, 'wb') as f:
                shutil.copyfileobj(r.raw, f)
        
        # 3. Unzip and Overwrite
        print("📦 Extracting and updating files...")
        with zipfile.ZipFile(save_path, 'r') as zip_ref:
            # Note: GitHub zip usually contains a top-level directory (e.g. Repo-v1.0/)
            # We need to strip it or handle it.
            # If using custom asset created by our workflow, it might be flat or nested depending on `zip` command.
            # Our `release.yml` uses `zip -r Video-Skill-Transcriber-vX.X.zip .` which makes it ROOT based (no extra folder usually if ran inside).
            # Wait, `zip -r file.zip .` includes `.` structure.
            
            # Let's extract to temp and move
            temp_dir = "update_temp"
            os.makedirs(temp_dir, exist_ok=True)
            zip_ref.extractall(temp_dir)
            
            # Move files from temp_dir to current dir
            # Check if temp_dir has single subfolder?
            items = os.listdir(temp_dir)
            if len(items) == 1 and os.path.isdir(os.path.join(temp_dir, items[0])):
                # Nested folder from GitHub Source Zip
                source_root = os.path.join(temp_dir, items[0])
            else:
                # Flat structure (our custom zip)
                source_root = temp_dir
            
            # Copy all files
            shutil.copytree(source_root, ".", dirs_exist_ok=True)
            
            # Cleanup
            shutil.rmtree(temp_dir)
            os.remove(save_path)
            
        print(f"✅ Successfully updated to {latest_tag}!")
        
    except Exception as e:
        print(f"❌ Update Failed: {e}")

if __name__ == "__main__":
    if Path(".git").exists():
        update_via_git()
    else:
        update_via_zip()
