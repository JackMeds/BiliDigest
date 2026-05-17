# 哔哩字幕笔记

面向个人 Agent 工作流的 B站字幕导出工具。

**BiliSubNotes / 哔哩字幕笔记** 用于读取本人已登录 B站账号可访问的视频，把“稍后再看”和“收藏夹”中的现成字幕、B站 AI 小助手总结导出为 Markdown/SRT/JSON，方便 Hermes Agent、Codex 或其他 Agent 做总结、笔记和知识整理。

## 功能

- 使用统一的用户数据目录 session，并兼容迁移旧版 `.user_session.json`。
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
python -m tools.bilisub auth import-browser edge
python -m tools.bilisub auth login
```

默认登录态统一保存到 macOS 用户数据目录：

```text
~/Library/Application Support/BiliSubNotes/session.json
```

`auth import-browser edge` 会通过 `yt-dlp` 导入 Microsoft Edge 里的 B站 Cookie，并保存到这份共享 session。扫码登录仍然保留：它会同时输出紧凑终端二维码、可复制登录 URL，并保存图片到 `output/login_qr.png`。旧版项目根目录 `.user_session.json` 只作为兼容 fallback；如果存在且有效，会尽量迁移到共享 session。

如果调用方是 Hermes Agent、Telegram bot 或 TUI，使用非阻塞 JSON 登录流程：

```bash
python -m tools.bilisub auth login --json --no-wait
python -m tools.bilisub auth poll <qrcode_key> --json
python -m tools.bilisub auth status --json
```

第一条命令会返回 `login_url`、`qr_image`、`qrcode_key` 和 `poll_command`。聊天 Agent 把 URL 或二维码图片发给用户，再轮询直到状态变成 `logged_in`、`expired`、`scanned` 或 `pending`。

查看当前共享 session 位置：

```bash
python -m tools.bilisub auth session-path --json
```

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

仓库采用 Agent Skills 标准目录：每个 Skill 是一个目录，目录内必须有 `SKILL.md`。因此标准安装器可以直接发现它：

```bash
npx skills add . --list
npx skills add . --skill bilisub-notes -g -a codex -y
```

如果从这个私有 GitHub 仓库安装，HTTPS 可以复用本机 GitHub 凭据：

```bash
npx skills add https://github.com/JackMeds/Video-Skill-Transcriber --skill bilisub-notes -g -a codex -y
```

SSH 形式也可以，但前提是 `ssh -T git@github.com` 能通过。本机当前 GitHub SSH 未打通，所以更建议用 HTTPS 或本地路径。

`npx skills` 安装的是 Skill 指令，不会自动安装 Python 项目本体。仍然需要保留本仓库 clone 和 `.venv` 依赖。Skill 内置了 `skills/bilisub-notes/scripts/bilisub` 启动器，会通过 `BILISUBNOTES_HOME` 或默认本机路径找到真正的 CLI。

本机开发时也可以继续用软链接安装，优点是改 Skill 文档后立即生效：

```bash
python install.py --target ~/.agents/skills
```

日常更新可以这样做：

```bash
git pull
npx skills add . --skill bilisub-notes -g -a codex -y
```

## 安全默认值

- 批量命令默认最多处理 `15` 条。
- 请求默认故意很慢：每次 API 调用大约等待 `8-12` 秒。可以用 `BILISUB_DELAY_SECONDS` 和 `BILISUB_DELAY_JITTER_SECONDS` 调整。
- 旧的视频/音频下载入口也会使用单 fragment 和慢速 `yt-dlp` sleep 参数。可以用 `BILISUB_YTDLP_SLEEP_SECONDS` 和 `BILISUB_YTDLP_MAX_SLEEP_SECONDS` 调整。
- 遇到 HTTP `412` 或 B站 `-352` 等风控信号会停止批处理。
- Cookie、Session、`.env` 和输出目录均被 Git 忽略。
- 只处理本人账号本来就能访问的内容。

## 鸣谢

BiliSubNotes 的功能边界和安全策略参考了开源 B站工具的实践，特别是 [BiliTools](https://github.com/btjawa/BiliTools)。本项目不迁入 BiliTools 的 Tauri UI，只保留轻量 Python CLI，供本地 Agent 使用。
