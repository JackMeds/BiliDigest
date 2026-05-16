# BiliSubNotes

Private Bilibili subtitle notes for agents.

**BiliSubNotes** exports subtitles and Bilibili AI summaries from videos that your own logged-in Bilibili account can already access. It is designed for local agent workflows such as Hermes Agent, Codex, or other assistants that need readable Markdown from your Watch Later and Favorites lists.

[中文说明](README_zh-CN.md)

## What It Does

- Reads your Bilibili login session from local `.user_session.json`.
- Lists Watch Later and Favorite folders/items.
- Exports existing Bilibili subtitles first, without running ASR by default.
- Exports Bilibili AI Assistant summaries when available.
- Writes Markdown, SRT, and JSON under `output/bilisub/<date>/`.
- Keeps Whisper/Qwen/OpenAI/Gemini transcription tools as explicit fallbacks.

This is not a public API documentation project and not a third-party Bilibili client. It is a private local tool for personal notes.

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Login

```bash
python -m tools.bilisub auth status
python -m tools.bilisub auth login
```

The QR login command prints a compact terminal QR, a copyable login URL, and writes `output/login_qr.png`. The session is saved to `.user_session.json`, which is ignored by Git.

For chat agents such as Hermes Agent, Telegram bots, or a TUI, use the non-blocking JSON login flow:

```bash
python -m tools.bilisub auth login --json --no-wait
python -m tools.bilisub auth poll <qrcode_key> --json
python -m tools.bilisub auth status --json
```

The first command returns `login_url`, `qr_image`, `qrcode_key`, and `poll_command`. Send the URL or QR image to the user, then poll until the response status becomes `logged_in`, `expired`, `scanned`, or `pending`.

## Usage

```bash
# Watch Later
python -m tools.bilisub list watch-later --limit 15

# Favorite folders for your own account
python -m tools.bilisub list favorites --mid me

# Items in a favorite folder
python -m tools.bilisub list favorite --media-id 123456 --limit 15

# Export subtitles
python -m tools.bilisub transcript BVxxxxxxxxxx --format md
python -m tools.bilisub transcript "https://www.bilibili.com/video/BVxxxxxxxxxx" --format srt

# Export Bilibili AI Assistant summary
python -m tools.bilisub summary BVxxxxxxxxxx

# Batch Watch Later
python -m tools.bilisub batch watch-later --limit 15 --with-summary
```

Legacy commands such as `python -m tools.auth --status`, `python -m tools.list --watch-later`, and `python -m tools.batch_run` still work as compatibility wrappers.

## Agent Skill

The skill lives at:

```text
skills/bilisub-notes/
```

Install or refresh the local Codex/OpenAI skill symlink:

```bash
python install.py --target ~/.codex/.agents/skills
```

## Safety Defaults

- Batch commands default to `15` items.
- Risk-control responses such as HTTP `412` or Bilibili `-352` stop batch processing.
- Cookies, sessions, `.env`, and output files are ignored by Git.
- The tool only processes content your logged-in account can already access.

## Acknowledgements

BiliSubNotes was shaped by practical behavior observed in open-source Bilibili tooling, especially [BiliTools](https://github.com/btjawa/BiliTools). This repository does not import the BiliTools Tauri UI; it keeps a small Python CLI surface for local agent use.
