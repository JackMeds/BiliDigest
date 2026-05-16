---
name: bilisub-notes
description: Export subtitles and Bilibili AI summaries from the user's own logged-in Watch Later and Favorites lists for local agent notes.
origin: BiliSubNotes
---

# BiliSubNotes

Use this skill when the user asks to summarize, inspect, or take notes from Bilibili Watch Later, Favorites, or a specific Bilibili video.

## Commands

Run commands from the BiliSubNotes project root.

```bash
python -m tools.bilisub auth status
python -m tools.bilisub auth import-browser edge
python -m tools.bilisub auth session-path --json
python -m tools.bilisub auth login
python -m tools.bilisub auth login --json --no-wait
python -m tools.bilisub auth poll <qrcode_key> --json
python -m tools.bilisub list watch-later --limit 15
python -m tools.bilisub list favorites --mid me
python -m tools.bilisub list favorite --media-id <id> --limit 15
python -m tools.bilisub transcript <BV-or-url> --format md
python -m tools.bilisub summary <BV-or-url>
python -m tools.bilisub batch watch-later --limit 15 --with-summary
```

## Workflow

1. Check login status first.
2. If login is missing and the user uses Microsoft Edge, prefer `auth import-browser edge` before QR login.
3. For a list request, fetch at most 15 items unless the user explicitly asks for a smaller number.
4. For a video, export Bilibili's existing subtitle first. Do not run ASR unless the subtitle export fails and the user asks for fallback transcription.
5. Read the generated Markdown from `output/bilisub/<date>/` and summarize or organize notes from that text.
6. If Bilibili returns risk-control or login errors, stop and tell the user to re-login or retry later.

## Chat Login Flow

For chat surfaces such as Hermes Agent, Telegram, or a TUI, do not block forever inside an interactive login command. Run:

```bash
python -m tools.bilisub auth login --json --no-wait
```

Send the returned `login_url` or `qr_image` to the user. Then poll with:

```bash
python -m tools.bilisub auth poll <qrcode_key> --json
```

Treat `logged_in` as success, `expired` as a request to regenerate the QR code, `scanned` as waiting for phone confirmation, and `pending` as still waiting for the scan.

## Session Storage

The shared macOS session path is:

```text
~/Library/Application Support/BiliSubNotes/session.json
```

Do not store session files inside individual Skill directories. Use `auth session-path --json` to confirm where the CLI is reading from.

## Safety

Only process videos the user's own account can already access. Do not expose, print, or copy `.user_session.json`, cookies, API keys, or `.env` values into chat.

The CLI intentionally waits about 8-12 seconds between API requests. Do not override the delay for routine daily automation unless the user explicitly asks. The legacy yt-dlp downloader also runs with slow sleeps and one concurrent fragment by default.
