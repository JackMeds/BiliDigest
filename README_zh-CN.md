# 哔哩字幕笔记

面向个人 Agent 工作流的 B站字幕导出工具。

**BiliSubNotes / 哔哩字幕笔记** 用于读取本人已登录 B站账号可访问的视频，把“稍后再看”和“收藏夹”中的现成字幕、B站 AI 小助手总结导出为 Markdown/SRT/JSON，方便 Hermes Agent、Codex 或其他 Agent 做总结、笔记和知识整理。

## 功能

- 使用本地 `.user_session.json` 登录态。
- 列出稍后再看、收藏夹目录、收藏夹内容。
- 优先使用 B站已有字幕，不默认跑 ASR。
- 可导出 B站 AI 小助手总结。
- 输出到 `output/bilisub/<日期>/`。
- Whisper/Qwen/OpenAI/Gemini 保留为显式 fallback，不再作为主流程。

本项目不是 B站 API 文档库，也不是公开第三方客户端。定位是本地私有自用的 Agent 辅助工具。

## 安装

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 登录

```bash
python -m tools.bilisub auth status
python -m tools.bilisub auth login
```

扫码登录会同时输出紧凑终端二维码、可复制登录 URL，并保存图片到 `output/login_qr.png`。登录态保存为 `.user_session.json`，不会被 Git 跟踪。

## 使用

```bash
# 稍后再看
python -m tools.bilisub list watch-later --limit 15

# 本人收藏夹目录
python -m tools.bilisub list favorites --mid me

# 指定收藏夹内容
python -m tools.bilisub list favorite --media-id 123456 --limit 15

# 导出字幕
python -m tools.bilisub transcript BVxxxxxxxxxx --format md
python -m tools.bilisub transcript "https://www.bilibili.com/video/BVxxxxxxxxxx" --format srt

# 导出 B站 AI 小助手总结
python -m tools.bilisub summary BVxxxxxxxxxx

# 批量处理稍后再看
python -m tools.bilisub batch watch-later --limit 15 --with-summary
```

旧命令仍保留兼容：`python -m tools.auth --status`、`python -m tools.list --watch-later`、`python -m tools.batch_run`。

## Agent Skill

Skill 位于：

```text
skills/bilisub-notes/
```

安装或刷新本机 Codex/OpenAI skill 软链接：

```bash
python install.py --target ~/.codex/.agents/skills
```

## 安全默认值

- 批量命令默认最多处理 `15` 条。
- 遇到 HTTP `412` 或 B站 `-352` 等风控信号会停止批处理。
- Cookie、Session、`.env` 和输出目录均被 Git 忽略。
- 只处理本人账号本来就能访问的内容。

## 鸣谢

BiliSubNotes 的功能边界和安全策略参考了开源 B站工具的实践，特别是 [BiliTools](https://github.com/btjawa/BiliTools)。本项目不迁入 BiliTools 的 Tauri UI，只保留轻量 Python CLI，供本地 Agent 使用。
