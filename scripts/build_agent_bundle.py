#!/usr/bin/env python3
"""Build an agent bundle, failing before publishing if its wheel differs from source."""
import argparse
import hashlib
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import zipfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument("--no-build-isolation", action="store_true")
    args = parser.parse_args()
    root = pathlib.Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    from tools.agent import VERSION
    with tempfile.TemporaryDirectory() as temp:
        work = pathlib.Path(temp)
        command = [sys.executable, "-m", "pip", "wheel", "--no-deps", str(root), "--wheel-dir", str(work)]
        if args.no_build_isolation:
            command.append("--no-build-isolation")
        subprocess.run(command, check=True)
        wheel = next(work.glob("bilidigest-*.whl"))
        with zipfile.ZipFile(wheel) as archive:
            for source in (root / "tools").rglob("*.py"):
                if archive.read(source.relative_to(root).as_posix()) != source.read_bytes():
                    raise RuntimeError(f"Stale wheel module: {source.relative_to(root)}")
        bundle = work / f"BiliDigest-Agent-{VERSION}"
        bundle.mkdir()
        shutil.copy2(wheel, bundle / wheel.name)
        shutil.copy2(root / "docs/agent-tools.md", bundle / "README.md")
        shutil.copy2(root / "scripts/agent_http_client.py", bundle / "agent_http_client.py")
        shutil.copy2(root / "LICENSE", bundle / "LICENSE")
        shutil.copy2(root / "NOTICE", bundle / "NOTICE")
        shutil.copytree(root / "skills/bili-digest", bundle / "bili-digest", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        (bundle / "install.py").write_text('''import pathlib, subprocess, sys
wheel = next(pathlib.Path(__file__).resolve().parent.glob("bilidigest-*.whl"))
subprocess.run([sys.executable, "-m", "pip", "install", str(wheel) + "[http,llm,browser]"], check=True)
print("Installed. Run: bili doctor")
''', encoding="utf-8")
        (bundle / "START_HERE.md").write_text('''# 给 Agent 的接入入口

此包包括可安装Python wheel、Skill、无依赖HTTP客户端及完整说明，不包含账号凭据或ASR模型。

有终端能力：用 Python 3.10+ 执行 `python install.py`，然后 `bili doctor`、`bili auth status`。读取 `bili-digest/SKILL.md`，按 discover → snapshot → plan → start → status → export 调用。

只有HTTP工具：在用户控制的机器上运行 `bili serve`，通过私有HTTPS入口连接，带Bearer认证读取 `/openapi.json`。也可以使用本包 `agent_http_client.py`。凭据由宿主的秘密配置提供，不放进聊天文本。

先读返回JSON中的作业state再报告完成。不是所有聊天界面都提供终端／HTTP能力；本包不会自动注册Dot或Grok Bot的权限。原始音轨、字幕、转写和摘要各有清楚的状态与来源。

说明中的 `pip install '.[http]'` 适用于源码仓库；此发行包请用 `python install.py` 或安装随附wheel。
''', encoding="utf-8")
        from tools.agent.http import create_app
        from tools.agent.store import Store
        app = create_app(Store(work / "schema-data", work / "schema-output"), "schema-only-placeholder-" + "x" * 32)
        (bundle / "openapi.json").write_text(json.dumps(app.openapi(), ensure_ascii=False, indent=2), encoding="utf-8")
        hashes = {str(p.relative_to(bundle)): hashlib.sha256(p.read_bytes()).hexdigest() for p in bundle.rglob("*") if p.is_file()}
        (bundle / "SHA256.json").write_text(json.dumps(hashes, ensure_ascii=False, indent=2), encoding="utf-8")
        args.output.mkdir(parents=True, exist_ok=True)
        archive_path = args.output / (bundle.name + ".zip")
        with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
            for p in bundle.rglob("*"):
                if p.is_file():
                    z.write(p, str(p.relative_to(work)))
        shutil.copy2(wheel, args.output / wheel.name)
        print(json.dumps({"bundle": str(archive_path.resolve()), "wheel": str((args.output / wheel.name).resolve()), "source_parity": "verified"}))


if __name__ == "__main__":
    main()
