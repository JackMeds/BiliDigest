# 哔哩摘要笔记

## Agent 工具 0.4.1

Apple Silicon 本地转写新增 Qwen3-ASR 0.6B MLX 8-bit（`.[qwen]`），支持分段缓存恢复；配置后新计划默认使用Qwen。时间戳为约20秒音频边界，不是逐字对齐。详见 [ASR配置](docs/agent-tools.md)。

现已提供可安装的 `bili` JSON CLI 和带 Bearer 认证的 HTTP API，供有终端或HTTP工具能力的 Agent 调用，不依赖 MCP。支持整 UP 主分页、全部分P、音轨优先、现成字幕、本机缺字幕转写、持久作业与知识库导出。

```sh
python -m pip install '.[http]'
bili doctor
bili auth status
bili discover 'https://space.bilibili.com/38291171'
```

[完整 Agent 使用说明、远程接入与恢复方式](docs/agent-tools.md)。`bilidigest agent ...` 等价于 `bili ...`；下方旧版稍后再看与收藏摘要命令保持兼容。默认安装不再强制安装PyTorch，旧转写模型依赖可用 `.[legacy]` 安装。


面向个人 Agent 工作流的 B站收藏与稍后再看摘要工具。

许可证：GPL-3.0-or-later。

**BiliDigest / 哔哩摘要笔记** 用于读取本人已登录 B站账号可访问的视频，把“稍后再看”和“收藏夹”中的内容整理成 Markdown/SRT/JSON，方便 Hermes Agent、Codex 或其他 Agent 做总结、笔记和知识整理。它优先使用 B站现成字幕和 B站 AI 小助手总结，也保留 ASR/大模型转写作为显式 fallback。

## 功能

- 使用统一的用户数据目录 session，并兼容迁移旧版 `.user_session.json`。
- 列出稍后再看、收藏夹目录、收藏夹内容。
- 稍后再看列表会缓存到本地，避免 Agent 重启后反复拉取 500+ 条列表。
- 列表命令会返回远端 `total`，即使用 `--limit 1` 也能快速知道稍后再看/收藏夹总数。
- 批量任务带持久状态文件，支持断点续跑、跳过已完成和失败项。
- 优先使用 B站已有字幕，不默认跑 ASR。
- 可导出 B站 AI 小助手总结。
- 人工产物输出到 `~/Documents/BiliDigest/bilidigest/<日期>/`。
- Whisper/Qwen/OpenAI/Gemini 保留为显式 fallback，不再作为主流程。

本项目不是 B站 API 文档库，也不是第三方客户端。定位是本地优先的个人 Agent 辅助工具。

## 安装

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 登录

```bash
python -m tools.bilidigest auth status
python -m tools.bilidigest auth import-browser edge
python -m tools.bilidigest auth login
```

默认登录态统一保存到 macOS 用户数据目录：

```text
~/Library/Application Support/BiliDigest/session.json
```

`auth import-browser edge` 会通过 `yt-dlp` 导入 Microsoft Edge 里的 B站 Cookie，并保存到这份共享 session。扫码登录仍然保留：它会同时输出紧凑终端二维码、可复制登录 URL，并保存图片到 `~/Library/Caches/BiliDigest/login_qr.png`。旧版 BiliSubNotes session 和项目根目录 `.user_session.json` 只作为兼容 fallback；如果存在且有效，会尽量迁移到共享 session。

## 运行目录

默认 macOS 目录按用途分开：

```text
状态/授权：~/Library/Application Support/BiliDigest/
可删缓存：~/Library/Caches/BiliDigest/
日志：~/Library/Logs/BiliDigest/
人工产物：~/Documents/BiliDigest/
```

`BILIDIGEST_HOME` 仍只用于定位源码仓库。需要临时改运行数据位置时，可以使用 `BILIDIGEST_DATA_DIR`、`BILIDIGEST_CACHE_DIR`、`BILIDIGEST_LOG_DIR`、`BILIDIGEST_OUTPUT_DIR` 覆盖默认目录。

清理边界：`Caches` 和 `Logs` 可以按需删除；`Application Support` 里有 session 和批处理状态，不要随便删；`Documents/BiliDigest` 是人要看的字幕、摘要、报告和静态站点产物。

如果调用方是 Hermes Agent、Telegram bot 或 TUI，使用非阻塞 JSON 登录流程：

```bash
python -m tools.bilidigest auth login --json --no-wait
python -m tools.bilidigest auth poll <qrcode_key> --json
python -m tools.bilidigest auth status --json
```

第一条命令会返回 `login_url`、`qr_image`、`qrcode_key` 和 `poll_command`。聊天 Agent 把 URL 或二维码图片发给用户，再轮询直到状态变成 `logged_in`、`expired`、`scanned` 或 `pending`。

查看当前共享 session 位置：

```bash
python -m tools.bilidigest auth session-path --json
```

## 使用

```bash
# 稍后再看
python -m tools.bilidigest list watch-later --limit 15
python -m tools.bilidigest list watch-later --limit 600 --no-items

# 本人收藏夹目录
python -m tools.bilidigest list favorites --mid me

# 指定收藏夹内容
python -m tools.bilidigest list favorite --media-id 123456 --limit 15

# 导出字幕
python -m tools.bilidigest transcript BVxxxxxxxxxx --format md
python -m tools.bilidigest transcript "https://www.bilibili.com/video/BVxxxxxxxxxx" --format srt

# 导出 B站 AI 小助手短总结（只作为参考/无字幕 fallback，不是最终摘要）
python -m tools.bilidigest summary BVxxxxxxxxxx

# 批量处理稍后再看；--with-summary 会基于完整字幕生成 .digest.md 深度摘要
python -m tools.bilidigest batch watch-later --limit 15 --with-summary
python -m tools.bilidigest batch watch-later --limit 600 --fallback-summary --with-summary
```

旧命令仍保留兼容：`python -m tools.auth --status`、`python -m tools.list --watch-later`、`python -m tools.batch_run`。

### 批量处理和续跑

`batch watch-later` 默认使用本地缓存和状态文件：

```text
~/Library/Caches/BiliDigest/bilidigest/cache/watch-later.jsonl
~/Library/Caches/BiliDigest/bilidigest/cache/watch-later.meta.json
~/Library/Caches/BiliDigest/bilidigest/snapshots/watch-later.json
~/Library/Application Support/BiliDigest/state/watch-later.json
```

默认列表缓存有效期是 24 小时。每次刷新列表时会更新快照并记录 `added`、`removed`、`changed`，方便日更自动化判断新增和移除。日常自动化或 Hermes Agent 重启后，直接重复运行同一条 `batch` 命令即可续跑；已完成视频会跳过，之前失败的视频也会跳过，避免反复请求同一个视频。

常用参数：

```bash
# 强制刷新稍后再看列表
python -m tools.bilidigest batch watch-later --limit 600 --refresh-list

# 每天自动化：刷新列表，但只处理本次快照新增的视频，并生成字幕深度摘要
python -m tools.bilidigest batch watch-later --limit 600 --refresh-list --only-new --fallback-summary --with-summary

# 忽略旧状态，从当前列表重新处理
python -m tools.bilidigest batch watch-later --limit 600 --no-resume
```

`--retry-failed` 只适合人工排查某个短时间故障后手动使用，不要放进日常自动化或大批量后台任务。无字幕、无 AI 总结的视频失败一次就应保留失败状态。

`--with-summary` 会读取完整 B站字幕，先做常见 ASR/错别字纠正，再生成 `.digest.md` 深度摘要；`summary` 字段会指向这个 digest，便于后续报告和飞书发布读取。B站 AI 小助手短总结只在显式 `--with-bili-summary` 或无字幕 `--fallback-summary` 时使用。如果视频没有 B站现成字幕，`--fallback-summary` 会尝试导出 B站 AI 小助手总结，并把该条记录为 `summary_only`。遇到登录失效、HTTP `412`、B站 `-352` 等风控信号时，批处理会保存状态并停止。

字幕深度摘要使用 OpenAI-compatible 接口，默认读取 `DEEPSEEK_API_KEY` 并使用 `deepseek-chat`；也可通过 `BILIDIGEST_LLM_API_KEY`、`BILIDIGEST_LLM_BASE_URL`、`BILIDIGEST_LLM_MODEL` 覆盖。

### 旧产物迁移

仓库旧版 `output/` 不再作为运行数据目录。需要迁移旧产物时运行：

```bash
python scripts/migrate_bilidigest_paths.py
```

脚本会把旧报告、站点、日期产物和 Feishu-ready 文件复制到 `~/Documents/BiliDigest/legacy-output/`，把旧缓存/快照复制到 `~/Library/Caches/BiliDigest/`，把旧状态复制到 `~/Library/Application Support/BiliDigest/state/`。复制校验通过后，原 `output/` 只会重命名为 `output.migrated-YYYYMMDD-HHMMSS`，不会直接删除。

## Agent Skill

Skill 位于：

```text
skills/bili-digest/
```

仓库采用 Agent Skills 标准目录：每个 Skill 是一个目录，目录内必须有 `SKILL.md`。因此标准安装器可以直接发现它：

```bash
npx skills add . --list
npx skills add . --skill bili-digest -g -a codex -y
```

如果从公开 GitHub 仓库安装，HTTPS 可以直接使用：

```bash
npx skills add https://github.com/JackMeds/BiliDigest --skill bili-digest -g -a codex -y
```

SSH 形式也可以，但前提是 `ssh -T git@github.com` 能通过。本机当前 GitHub SSH 未打通，所以更建议用 HTTPS 或本地路径。

`npx skills` 安装的是 Skill 指令，不会自动安装 Python 项目本体。仍然需要保留本仓库 clone 和 `.venv` 依赖。Skill 内置了 `skills/bili-digest/scripts/bilidigest` 启动器，会通过 `BILIDIGEST_HOME` 或默认本机路径找到真正的 CLI。

本机开发时也可以继续用软链接安装，优点是改 Skill 文档后立即生效：

```bash
python install.py --target ~/.agents/skills
```

日常更新可以这样做：

```bash
git pull
npx skills add . --skill bili-digest -g -a codex -y
```

## 安全默认值

- 批量命令默认最多处理 `15` 条。
- 请求默认故意很慢：每次 API 调用大约等待 `8-12` 秒。可以用 `BILIDIGEST_DELAY_SECONDS` 和 `BILIDIGEST_DELAY_JITTER_SECONDS` 调整。
- 大批量处理建议使用默认慢速或稍微调到 `BILIDIGEST_DELAY_SECONDS=6 BILIDIGEST_DELAY_JITTER_SECONDS=2`，不要并发启动多个批处理。
- 旧的视频/音频下载入口也会使用单 fragment 和慢速 `yt-dlp` sleep 参数。可以用 `BILIDIGEST_YTDLP_SLEEP_SECONDS` 和 `BILIDIGEST_YTDLP_MAX_SLEEP_SECONDS` 调整。
- 遇到 HTTP `412` 或 B站 `-352` 等风控信号会停止批处理。
- Cookie、Session、`.env` 和运行产物均被 Git 忽略。
- 只处理本人账号本来就能访问的内容。

## 鸣谢

BiliDigest 的功能边界和安全策略参考了开源 B站工具的实践，特别是采用 GPL-3.0-or-later 协议的 [BiliTools](https://github.com/btjawa/BiliTools)。本项目不迁入 BiliTools 的 Tauri UI，只保留轻量 Python CLI，供本地 Agent 使用。归属和参考说明见 [NOTICE](NOTICE)。
