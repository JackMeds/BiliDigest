import os
import sys
import argparse
from pathlib import Path
import shutil

def install_skill(target_dir=None):
    """
    Installs the current Video-Skill-Transcriber into the Agent's skills directory.
    """
    # 1. Determine Source (Current Directory)
    source_path = Path(__file__).parent.resolve()
    
    # 2. Determine Target
    if not target_dir:
        # Default locations to check
        possible_targets = [
            Path(".agent/skills"),
            Path.home() / ".agent/skills",
            Path.home() / ".config/opencode/skills" 
        ]
        
        # Try to find existing one
        for p in possible_targets:
            if p.exists():
                target_dir = p
                print(f"📍 Auto-detected skills directory: {target_dir}")
                break
        
        # Fallback if none found
        if not target_dir:
            target_dir = Path(".agent/skills")
            print(f"⚠️ No agent directory found. Creating default: {target_dir}")

    dest_path = Path(target_dir) / "video-transcriber"
    
    # 3. Installation (Symlink preferred for updates)
    print(f"🚀 Installing from {source_path} to {dest_path}...")
    
    if dest_path.exists():
        if dest_path.is_symlink() or dest_path.is_file():
            os.remove(dest_path)
        elif dest_path.is_dir():
            print(f"⚠️ Removing existing directory: {dest_path}")
            shutil.rmtree(dest_path)

    try:
        # Try Symlink first (best for git updates)
        # Note: Symlink requires source path to be the final location user wants to keep code in
        os.makedirs(dest_path.parent, exist_ok=True)
        os.symlink(source_path, dest_path)
        print("✅ Success! Installed via Symlink.")
        print("   (Code updates in this folder will automatically reflect in the Agent)")
    except OSError as e:
        print(f"⚠️ Symlink failed ({e}). Falling back to Copy...")
        shutil.copytree(source_path, dest_path, ignore=shutil.ignore_patterns(".git*", "__pycache__", "*.pyc"))
        print("✅ Success! Installed via Copy.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Install Video Skill to Agent")
    parser.add_argument("--target", "-t", help="Target skills directory (e.g. .agent/skills)")
    args = parser.parse_args()
    
    install_skill(args.target)
