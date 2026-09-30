---
name: bili-digest
description: Collect accessible Bilibili videos, UP uploads, favorites or Watch Later into audio, timestamped transcripts and knowledge-library artifacts using JSON CLI or authenticated HTTP.
metadata:
  origin: BiliDigest
---

# BiliDigest for agents

Use the installed `bili` JSON CLI when a terminal is available. For a remote service, use its authenticated OpenAPI API. MCP is not required. A Skill supplies instructions; the host still needs terminal execution or HTTP tools.

## First use

Run `bili doctor` and `bili auth status`. If the command is missing, install BiliDigest (`pip install '.[http]'` from its checkout or install its supplied wheel). A repository-local fallback is `scripts/bilidigest agent ...`; set `BILIDIGEST_HOME` only when the checkout cannot be found automatically.

Use `bili auth import-bilitools` for the user's existing local BiliTools session, or `bili auth login` then `bili auth poll KEY` for QR login. Never print or attach cookies, session files or HTTP tokens. Login/QR handling stays in the user's own account.

## Collection workflow

```sh
bili discover 'https://space.bilibili.com/38291171' --limit 1000
bili snapshot SNAPSHOT_ID --offset 0 --limit 100
bili plan SNAPSHOT_ID --mode audio-preferred --asr whisper-cpp --language zh
bili start PLAN_ID --key my-collection
bili status JOB_ID
bili export JOB_ID --include-media
```

Use IDs returned in `data.id`, not these placeholders. Discovery supports video BV/AV/URLs, b23.tv, UP spaces, `mid:UID`, `fav:FID`, favorite URLs with fid, and `watch-later`. It returns a preview; paginate `snapshot` to review all items. Confirm `complete` before claiming full coverage. Increase the discovery limit when necessary; `--allow-partial` is only for an intentionally limited collection.

For topic filtering, inspect titles/descriptions and use repeated `--select BV` / `--exclude BV`. `--keyword` is literal matching, not semantic relevance. Ambiguous titles may need transcript review. The collector expands all regular video parts automatically.

Media policy follows the user: `audio-preferred` saves standalone audio when available, otherwise a combined video with audio; `audio` extracts audio if needed; `video` saves video with sound. Do not claim video frames or diagrams were analyzed by a transcript-only workflow.

Subtitles are preferred. Choose `--asr whisper-cpp` when the user's request authorizes fallback transcription; otherwise the default is `--asr none`. `bili configure --whisper-model /path/to/model.bin` selects an already downloaded local model. Do not silently download large models. `--summarize` explicitly invokes the configured LLM on full transcript chunks, requires the llm extra/API configuration, and may incur provider cost.

## Long jobs and results

`start` returns a persistent job ID; `--foreground` waits. Inspect `state`, `counts`, per-part errors and output files. `ok:true` only means the tool call succeeded, not that all collection stages completed. Use `bili resume JOB_ID` after fixing a dependency/login problem; use `bili cancel JOB_ID` to stop while preserving work. Do not restart by creating a fresh job unless a new collection is intended.

A `complete` ASR-disabled job can legitimately lack transcripts; report those gaps. `partial` has failed stages, `blocked` needs login/risk-control handling. On platform risk-control errors stop requests and let the user resolve the challenge or retry later. Do not repeatedly retry blocked resources.

Read the generated `README.md` and manifest, then use per-part Markdown/SRT/JSON, `transcripts.md`, `catalog.csv` or `knowledge.jsonl`. Exact duplicate audio can reuse ASR, but each source remains identified. Never label title-based or sampled-text notes as full-transcript summaries. Keep automatic transcription uncertainties visible.

## HTTP-only hosts

A trusted deployment runs `bili serve`. Use Bearer authentication and fetch `/openapi.json`; it declares operations and inputs. Common sequence:

1. `POST /v1/discover` with `source` and `limit`.
2. `GET /v1/snapshots/{id}` with offset/limit.
3. `POST /v1/plans` with snapshot_id, select/exclude, mode, asr and language.
4. `POST /v1/jobs` with plan_id and idempotency_key.
5. `GET /v1/jobs/{id}` until a terminal state or required action.
6. `POST /v1/jobs/{id}/export`, then authenticated artifact download.

The endpoint must be reachable from the calling host. Local file paths are not cloud uploads; fetch the artifact through the API when transferring to a remote agent. The server never returns login cookies. The standalone `agent_http_client.py` uses only Python's standard library.

## Existing daily digest users

For the earlier watch-later daily automation and its compatibility CLI, read [legacy.md](references/legacy.md). Those commands remain available; do not replace existing schedules just because the new collector exists.
