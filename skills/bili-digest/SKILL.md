---
name: bili-digest
description: Summarize and organize the user's own logged-in Bilibili Watch Later and Favorites lists for local agent notes.
origin: BiliDigest
---

# BiliDigest

Use this skill when the user asks to summarize, inspect, or take notes from Bilibili Watch Later, Favorites, or a specific Bilibili video.

This repository is GPL-3.0-or-later and includes attribution notes for BiliTools in `NOTICE`.

## Commands

Prefer the bundled launcher next to this `SKILL.md` so the skill also works when installed outside the repository:

```bash
scripts/bilidigest auth status
scripts/bilidigest auth import-browser edge
scripts/bilidigest auth session-path --json
scripts/bilidigest auth login --json --no-wait
scripts/bilidigest auth poll <qrcode_key> --json
scripts/bilidigest list watch-later --limit 15
scripts/bilidigest list watch-later --limit 600 --no-items
scripts/bilidigest transcript <BV-or-url> --format md
scripts/bilidigest summary <BV-or-url>
scripts/bilidigest batch watch-later --limit 600 --fallback-summary --with-summary
```

If the launcher cannot find the repository, set `BILIDIGEST_HOME` to the cloned BiliDigest path. When already inside the BiliDigest project root, these direct commands are equivalent:

```bash
python -m tools.bilidigest auth status
python -m tools.bilidigest auth import-browser edge
python -m tools.bilidigest auth session-path --json
python -m tools.bilidigest auth login
python -m tools.bilidigest auth login --json --no-wait
python -m tools.bilidigest auth poll <qrcode_key> --json
python -m tools.bilidigest list watch-later --limit 15
python -m tools.bilidigest list watch-later --limit 600 --no-items
python -m tools.bilidigest list favorites --mid me
python -m tools.bilidigest list favorite --media-id <id> --limit 15
python -m tools.bilidigest transcript <BV-or-url> --format md
python -m tools.bilidigest summary <BV-or-url>
python -m tools.bilidigest batch watch-later --limit 15 --with-summary
python -m tools.bilidigest batch watch-later --limit 600 --fallback-summary --with-summary
```

## Workflow

1. Check login status first.
2. If login is missing and the user uses Microsoft Edge, prefer `auth import-browser edge` before QR login.
3. For a list request, fetch at most 15 items unless the user explicitly asks for a smaller number.
4. For a video, export Bilibili's existing subtitle first. Do not run ASR unless the subtitle export fails and the user asks for fallback transcription.
5. Read the generated Markdown from `output/bilidigest/<date>/` and summarize or organize notes from that text.
6. If Bilibili returns risk-control or login errors, stop and tell the user to re-login or retry later.

## Batch Workflow

For large Watch Later runs, prefer the resumable batch command:

```bash
scripts/bilidigest batch watch-later --limit 600 --fallback-summary --with-summary
```

The command stores local cache and state here:

```text
output/bilidigest/cache/watch-later.jsonl
output/bilidigest/cache/watch-later.meta.json
output/bilidigest/state/watch-later.json
```

Rerunning the same command resumes from the state file. Use `--refresh-list` when the user explicitly wants a fresh Watch Later list, `--retry-failed` when they want to retry previous failures, and `--no-resume` only when they want to ignore the old state.

## Chat Login Flow

For chat surfaces such as Hermes Agent, Telegram, or a TUI, do not block forever inside an interactive login command. Run:

```bash
python -m tools.bilidigest auth login --json --no-wait
```

Send the returned `login_url` or `qr_image` to the user. Then poll with:

```bash
python -m tools.bilidigest auth poll <qrcode_key> --json
```

Treat `logged_in` as success, `expired` as a request to regenerate the QR code, `scanned` as waiting for phone confirmation, and `pending` as still waiting for the scan.

## Session Storage

The shared macOS session path is:

```text
~/Library/Application Support/BiliDigest/session.json
```

Do not store session files inside individual Skill directories. Use `auth session-path --json` to confirm where the CLI is reading from.

## Safety

Only process videos the user's own account can already access. Do not expose, print, or copy `.user_session.json`, cookies, API keys, or `.env` values into chat.

The CLI intentionally waits about 8-12 seconds between API requests. Do not override the delay for routine daily automation unless the user explicitly asks. The legacy yt-dlp downloader also runs with slow sleeps and one concurrent fragment by default.

For one-off large local batches, a modest override such as `BILIDIGEST_DELAY_SECONDS=6 BILIDIGEST_DELAY_JITTER_SECONDS=2` is acceptable when the user explicitly asks to process hundreds of videos. Do not start multiple BiliDigest batch jobs at the same time.
