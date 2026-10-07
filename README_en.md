# BiliDigest

## Agent tools 0.4.1

Apple Silicon ASR now supports Qwen3-ASR 0.6B MLX 8-bit via the qwen extra, with resumable chunk caching. Timestamps represent approximately 20-second audio boundaries, not word alignment. See [configuration](docs/agent-tools.md).

An installable `bili` JSON CLI and authenticated HTTP/OpenAPI API now share the same collection engine. MCP is not required. Collect UP uploads and all regular video parts, prefer independent audio and existing subtitles, optionally transcribe locally, resume persistent jobs and export knowledge artifacts.

```sh
python -m pip install '.[http]'
bili doctor
bili auth status
```

[Agent usage and HTTP integration](docs/agent-tools.md). `bilidigest agent ...` is equivalent to `bili ...`; legacy commands below remain compatible. Heavy transcription packages are optional via `.[legacy]`. A chat host still needs terminal or HTTP tool capabilities.


Bilibili digest notes for agents.

[中文说明](README.md)

License: GPL-3.0-or-later.

**BiliDigest** helps agents summarize and organize videos from your own logged-in Bilibili Watch Later and Favorites lists. It prefers existing Bilibili subtitles and AI summaries when available, and keeps ASR/model-based transcription as an explicit fallback path.

## What It Does

- Reads your Bilibili login session from a shared user data file, with legacy `.user_session.json` migration.
- Lists Watch Later and Favorite folders/items.
- Caches large Watch Later lists locally so agents do not refetch hundreds of items on every restart.
- List commands return the remote `total`, so `--limit 1` can quickly report the Watch Later or Favorite size.
- Writes a persistent batch state file for resume and skip-completed/failed workflows.
- Exports existing Bilibili subtitles first, without running ASR by default.
- Exports Bilibili AI Assistant summaries when available.
- Writes Markdown, SRT, and JSON under `~/Documents/BiliDigest/bilidigest/<date>/`.
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

`auth import-browser edge` imports your existing Microsoft Edge Bilibili cookies through `yt-dlp` and stores them in that shared session file. The QR login command remains available; it prints a compact terminal QR, a copyable login URL, and writes `~/Library/Caches/BiliDigest/login_qr.png`. Old BiliSubNotes and project-local `.user_session.json` files are only used as legacy fallbacks and are migrated into the shared session file when possible.

## Runtime directories

Default macOS directories are split by purpose:

```text
Auth/state: ~/Library/Application Support/BiliDigest/
Disposable cache: ~/Library/Caches/BiliDigest/
Logs: ~/Library/Logs/BiliDigest/
Human-facing artifacts: ~/Documents/BiliDigest/
```

`BILIDIGEST_HOME` is still only used to locate the source checkout. To override runtime data locations, set `BILIDIGEST_DATA_DIR`, `BILIDIGEST_CACHE_DIR`, `BILIDIGEST_LOG_DIR`, or `BILIDIGEST_OUTPUT_DIR`.

Cleanup boundary: `Caches` and `Logs` are disposable; `Application Support` contains the session and long-lived batch state; `Documents/BiliDigest` contains subtitles, summaries, reports, and static site artifacts intended for humans.

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
python -m tools.bilidigest list watch-later --limit 600 --no-items

# Favorite folders for your own account
python -m tools.bilidigest list favorites --mid me

# Items in a favorite folder
python -m tools.bilidigest list favorite --media-id 123456 --limit 15

# Export subtitles
python -m tools.bilidigest transcript BVxxxxxxxxxx --format md
python -m tools.bilidigest transcript "https://www.bilibili.com/video/BVxxxxxxxxxx" --format srt

# Export the short Bilibili AI Assistant summary for reference/fallback only
python -m tools.bilidigest summary BVxxxxxxxxxx

# Batch Watch Later; --with-summary writes a transcript-based .digest.md
python -m tools.bilidigest batch watch-later --limit 15 --with-summary
python -m tools.bilidigest batch watch-later --limit 600 --fallback-summary --with-summary
```

Legacy commands such as `python -m tools.auth --status`, `python -m tools.list --watch-later`, and `python -m tools.batch_run` still work as compatibility wrappers.

### Batch Resume

`batch watch-later` uses local cache and state files by default:

```text
~/Library/Caches/BiliDigest/bilidigest/cache/watch-later.jsonl
~/Library/Caches/BiliDigest/bilidigest/cache/watch-later.meta.json
~/Library/Caches/BiliDigest/bilidigest/snapshots/watch-later.json
~/Library/Application Support/BiliDigest/state/watch-later.json
```

The default list cache TTL is 24 hours. Each refreshed list updates a snapshot and records `added`, `removed`, and `changed`, which lets daily automation detect new and removed items. For daily automation or after an agent restart, rerun the same `batch` command to resume. Completed videos and previously failed videos are skipped.

Common options:

```bash
# Force-refresh the Watch Later list
python -m tools.bilidigest batch watch-later --limit 600 --refresh-list

# Daily automation: refresh the list, process newly added items, and write transcript digests
python -m tools.bilidigest batch watch-later --limit 600 --refresh-list --only-new --fallback-summary --with-summary

# Ignore the old state and process the current list again
python -m tools.bilidigest batch watch-later --limit 600 --no-resume
```

`--retry-failed` is only for manual investigation after a short-lived outage. Do not put it in daily automation or large background batches. Videos without subtitles or AI summaries should remain failed after one attempt.

`--with-summary` reads the full Bilibili subtitle, applies common ASR/typo correction, and writes a `.digest.md` deep summary. The state `summary` field points to this digest so reports and Feishu publishing use the meaningful artifact. The short Bilibili AI Assistant summary is used only with explicit `--with-bili-summary` or no-subtitle `--fallback-summary`. If a video has no existing Bilibili subtitle, `--fallback-summary` attempts to export the Bilibili AI Assistant summary and records the item as `summary_only`. Login-expired and risk-control responses such as HTTP `412` or Bilibili `-352` save state and stop the batch.

Transcript digests use an OpenAI-compatible API. By default the tool reads `DEEPSEEK_API_KEY` and uses `deepseek-chat`; override with `BILIDIGEST_LLM_API_KEY`, `BILIDIGEST_LLM_BASE_URL`, and `BILIDIGEST_LLM_MODEL`.

### Legacy output migration

The project-local `output/` directory is no longer the runtime data directory. To migrate older files, run:

```bash
python scripts/migrate_bilidigest_paths.py
```

The script copies old reports, site files, dated artifacts, and Feishu-ready files into `~/Documents/BiliDigest/legacy-output/`, old cache and snapshots into `~/Library/Caches/BiliDigest/`, and old state into `~/Library/Application Support/BiliDigest/state/`. After copy verification, the original `output/` is renamed to `output.migrated-YYYYMMDD-HHMMSS`; it is not deleted.

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
- For large batches, keep the default slow mode or use a modest setting such as `BILIDIGEST_DELAY_SECONDS=6 BILIDIGEST_DELAY_JITTER_SECONDS=2`; do not run multiple batch jobs concurrently.
- The legacy video/audio downloader also uses one fragment at a time and passes slow `yt-dlp` sleep settings. Tune it with `BILIDIGEST_YTDLP_SLEEP_SECONDS` and `BILIDIGEST_YTDLP_MAX_SLEEP_SECONDS`.
- Risk-control responses such as HTTP `412` or Bilibili `-352` stop batch processing.
- Cookies, sessions, `.env`, and runtime artifacts are ignored by Git.
- The tool only processes content your logged-in account can already access.

## Acknowledgements

BiliDigest was shaped by practical behavior observed in open-source Bilibili tooling, especially [BiliTools](https://github.com/btjawa/BiliTools), which is licensed under GPL-3.0-or-later. This repository does not import the BiliTools Tauri UI; it keeps a small Python CLI surface for local agent use. See [NOTICE](NOTICE) for attribution notes.
