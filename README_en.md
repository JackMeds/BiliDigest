# BiliDigest

Bilibili digest notes for agents.

[中文说明](README.md)

License: GPL-3.0-or-later.

**BiliDigest** helps agents summarize and organize videos from your own logged-in Bilibili Watch Later and Favorites lists. It prefers existing Bilibili subtitles and AI summaries when available, and keeps ASR/model-based transcription as an explicit fallback path.

## What It Does

- Reads your Bilibili login session from a shared user data file, with legacy `.user_session.json` migration.
- Lists Watch Later and Favorite folders/items.
- Exports existing Bilibili subtitles first, without running ASR by default.
- Exports Bilibili AI Assistant summaries when available.
- Writes Markdown, SRT, and JSON under `output/bilidigest/<date>/`.
- Keeps Whisper/Qwen/OpenAI/Gemini transcription tools as explicit fallbacks.

This is not a public API documentation project and not a third-party Bilibili client. It is a local-first tool for personal notes and agent workflows.

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Login

```bash
python -m tools.bilidigest auth status
python -m tools.bilidigest auth import-browser edge
python -m tools.bilidigest auth login
```

The preferred login cache is the macOS user data file:

```text
~/Library/Application Support/BiliDigest/session.json
```

`auth import-browser edge` imports your existing Microsoft Edge Bilibili cookies through `yt-dlp` and stores them in that shared session file. The QR login command remains available; it prints a compact terminal QR, a copyable login URL, and writes `output/login_qr.png`. Old BiliSubNotes and project-local `.user_session.json` files are only used as legacy fallbacks and are migrated into the shared session file when possible.

For chat agents such as Hermes Agent, Telegram bots, or a TUI, use the non-blocking JSON login flow:

```bash
python -m tools.bilidigest auth login --json --no-wait
python -m tools.bilidigest auth poll <qrcode_key> --json
python -m tools.bilidigest auth status --json
```

The first command returns `login_url`, `qr_image`, `qrcode_key`, and `poll_command`. Send the URL or QR image to the user, then poll until the response status becomes `logged_in`, `expired`, `scanned`, or `pending`.

To see the shared session location:

```bash
python -m tools.bilidigest auth session-path --json
```

## Usage

```bash
# Watch Later
python -m tools.bilidigest list watch-later --limit 15

# Favorite folders for your own account
python -m tools.bilidigest list favorites --mid me

# Items in a favorite folder
python -m tools.bilidigest list favorite --media-id 123456 --limit 15

# Export subtitles
python -m tools.bilidigest transcript BVxxxxxxxxxx --format md
python -m tools.bilidigest transcript "https://www.bilibili.com/video/BVxxxxxxxxxx" --format srt

# Export Bilibili AI Assistant summary
python -m tools.bilidigest summary BVxxxxxxxxxx

# Batch Watch Later
python -m tools.bilidigest batch watch-later --limit 15 --with-summary
```

Legacy commands such as `python -m tools.auth --status`, `python -m tools.list --watch-later`, and `python -m tools.batch_run` still work as compatibility wrappers.

## Agent Skill

The skill lives at:

```text
skills/bili-digest/
```

The repository follows the Agent Skills layout: each skill is a directory with a required `SKILL.md` file. This means standard installers can discover it:

```bash
npx skills add . --list
npx skills add . --skill bili-digest -g -a codex -y
```

For the public GitHub repository, HTTPS works directly:

```bash
npx skills add https://github.com/JackMeds/BiliDigest --skill bili-digest -g -a codex -y
```

SSH install also works after `ssh -T git@github.com` succeeds. On this machine SSH auth is not currently configured for GitHub, so prefer HTTPS or the local path.

`npx skills` installs the skill instructions, not the Python project itself. Keep this repository cloned and dependencies installed. The skill includes `skills/bili-digest/scripts/bilidigest`, a small launcher that finds the clone via `BILIDIGEST_HOME` or the default local path.

For live development on this machine, a symlink install is still useful because edits reflect immediately:

```bash
python install.py --target ~/.agents/skills
```

For routine updates after a pull:

```bash
git pull
npx skills add . --skill bili-digest -g -a codex -y
```

## Safety Defaults

- Batch commands default to `15` items.
- Requests are deliberately slow by default: each API call waits about `8-12` seconds. You can tune this with `BILIDIGEST_DELAY_SECONDS` and `BILIDIGEST_DELAY_JITTER_SECONDS`.
- The legacy video/audio downloader also uses one fragment at a time and passes slow `yt-dlp` sleep settings. Tune it with `BILIDIGEST_YTDLP_SLEEP_SECONDS` and `BILIDIGEST_YTDLP_MAX_SLEEP_SECONDS`.
- Risk-control responses such as HTTP `412` or Bilibili `-352` stop batch processing.
- Cookies, sessions, `.env`, and output files are ignored by Git.
- The tool only processes content your logged-in account can already access.

## Acknowledgements

BiliDigest was shaped by practical behavior observed in open-source Bilibili tooling, especially [BiliTools](https://github.com/btjawa/BiliTools), which is licensed under GPL-3.0-or-later. This repository does not import the BiliTools Tauri UI; it keeps a small Python CLI surface for local agent use. See [NOTICE](NOTICE) for attribution notes.
