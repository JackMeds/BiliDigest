# BiliSubNotes

Private Bilibili subtitle notes for agents.

License: GPL-3.0-or-later.

**BiliSubNotes** exports subtitles and Bilibili AI summaries from videos that your own logged-in Bilibili account can already access. It is designed for local agent workflows such as Hermes Agent, Codex, or other assistants that need readable Markdown from your Watch Later and Favorites lists.

[中文说明](README_zh-CN.md)

## What It Does

- Reads your Bilibili login session from a shared user data file, with legacy `.user_session.json` migration.
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
python -m tools.bilisub auth import-browser edge
python -m tools.bilisub auth login
```

The preferred login cache is the macOS user data file:

```text
~/Library/Application Support/BiliSubNotes/session.json
```

`auth import-browser edge` imports your existing Microsoft Edge Bilibili cookies through `yt-dlp` and stores them in that shared session file. The QR login command remains available; it prints a compact terminal QR, a copyable login URL, and writes `output/login_qr.png`. Old project-local `.user_session.json` files are only used as a legacy fallback and are migrated into the shared session file when possible.

For chat agents such as Hermes Agent, Telegram bots, or a TUI, use the non-blocking JSON login flow:

```bash
python -m tools.bilisub auth login --json --no-wait
python -m tools.bilisub auth poll <qrcode_key> --json
python -m tools.bilisub auth status --json
```

The first command returns `login_url`, `qr_image`, `qrcode_key`, and `poll_command`. Send the URL or QR image to the user, then poll until the response status becomes `logged_in`, `expired`, `scanned`, or `pending`.

To see the shared session location:

```bash
python -m tools.bilisub auth session-path --json
```

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

The repository follows the Agent Skills layout: each skill is a directory with a required `SKILL.md` file. This means standard installers can discover it:

```bash
npx skills add . --list
npx skills add . --skill bilisub-notes -g -a codex -y
```

For this private GitHub repository, HTTPS works with your existing GitHub credentials:

```bash
npx skills add https://github.com/JackMeds/Video-Skill-Transcriber --skill bilisub-notes -g -a codex -y
```

SSH install also works after `ssh -T git@github.com` succeeds. On this machine SSH auth is not currently configured for GitHub, so prefer HTTPS or the local path.

`npx skills` installs the skill instructions, not the Python project itself. Keep this repository cloned and dependencies installed. The skill includes `skills/bilisub-notes/scripts/bilisub`, a small launcher that finds the clone via `BILISUBNOTES_HOME` or the default local path.

For live development on this machine, a symlink install is still useful because edits reflect immediately:

```bash
python install.py --target ~/.agents/skills
```

For routine updates after a pull:

```bash
git pull
npx skills add . --skill bilisub-notes -g -a codex -y
```

## Safety Defaults

- Batch commands default to `15` items.
- Requests are deliberately slow by default: each API call waits about `8-12` seconds. You can tune this with `BILISUB_DELAY_SECONDS` and `BILISUB_DELAY_JITTER_SECONDS`.
- The legacy video/audio downloader also uses one fragment at a time and passes slow `yt-dlp` sleep settings. Tune it with `BILISUB_YTDLP_SLEEP_SECONDS` and `BILISUB_YTDLP_MAX_SLEEP_SECONDS`.
- Risk-control responses such as HTTP `412` or Bilibili `-352` stop batch processing.
- Cookies, sessions, `.env`, and output files are ignored by Git.
- The tool only processes content your logged-in account can already access.

## Acknowledgements

BiliSubNotes was shaped by practical behavior observed in open-source Bilibili tooling, especially [BiliTools](https://github.com/btjawa/BiliTools), which is licensed under GPL-3.0-or-later. This repository does not import the BiliTools Tauri UI; it keeps a small Python CLI surface for local agent use. See [NOTICE](NOTICE) for attribution notes.
