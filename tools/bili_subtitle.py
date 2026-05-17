import json
from pathlib import Path
from typing import Any

from .bili_client import BiliClient, BiliError, RiskControl, dated_output_dir, sanitize_filename


LANG_PRIORITY = ["zh-CN", "zh-Hans", "ai-zh", "zh", "zh-TW"]


def srt_time(seconds: float) -> str:
    ms_total = int(round(seconds * 1000))
    hours, rem = divmod(ms_total, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    secs, ms = divmod(rem, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"


def choose_subtitle(subtitles: list[dict[str, Any]], lang: str | None = None) -> dict[str, Any]:
    if not subtitles:
        raise BiliError("No Bilibili subtitle is available for this video")
    if lang:
        for item in subtitles:
            if item.get("lan") == lang or item.get("lan_doc") == lang:
                return item
    for preferred in LANG_PRIORITY:
        for item in subtitles:
            if item.get("lan") == preferred:
                return item
    return subtitles[0]


def fetch_subtitle_json(client: BiliClient, subtitle_url: str) -> dict[str, Any]:
    url = "https:" + subtitle_url if subtitle_url.startswith("//") else subtitle_url
    client.throttle()
    resp = client.session.get(url, timeout=20)
    if resp.status_code == 412:
        raise RiskControl("HTTP 412 while downloading subtitle: request paused for account safety")
    resp.raise_for_status()
    return resp.json()


def body_to_srt(body: list[dict[str, Any]]) -> str:
    chunks = []
    for idx, line in enumerate(body, 1):
        chunks.append(
            f"{idx}\n{srt_time(float(line['from']))} --> {srt_time(float(line['to']))}\n{line.get('content', '').strip()}"
        )
    return "\n\n".join(chunks) + ("\n" if chunks else "")


def body_to_markdown(video: dict[str, Any], subtitle: dict[str, Any], body: list[dict[str, Any]]) -> str:
    lines = [
        f"# {video['title']}",
        "",
        f"- BV: {video['bvid']}",
        f"- URL: https://www.bilibili.com/video/{video['bvid']}",
        f"- Subtitle: {subtitle.get('lan_doc') or subtitle.get('lan')}",
        "",
        "## 字幕",
        "",
    ]
    for line in body:
        ts = int(float(line["from"]))
        text = line.get("content", "").strip()
        if text:
            lines.append(f"- [{ts // 60:02d}:{ts % 60:02d}](https://www.bilibili.com/video/{video['bvid']}?t={ts}) {text}")
    return "\n".join(lines).rstrip() + "\n"


def export_transcript(
    client: BiliClient,
    value: str,
    fmt: str = "md",
    lang: str | None = None,
    out_dir: Path | None = None,
) -> dict[str, Any]:
    video = client.video_info(value)
    pages = video.get("pages") or []
    if not pages:
        raise BiliError("Video has no playable pages")
    page = pages[0]
    aid = int(video["aid"])
    cid = int(page["cid"])
    player = client.player_info(aid, cid)
    subtitles = ((player.get("subtitle") or {}).get("subtitles") or [])
    picked = choose_subtitle(subtitles, lang)
    raw = fetch_subtitle_json(client, picked["subtitle_url"])
    body = raw.get("body") or []
    if not body:
        raise BiliError("Subtitle body is empty")

    target_dir = out_dir or dated_output_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    base = f"{sanitize_filename(video['title'])}-{video['bvid']}"
    json_path = target_dir / f"{base}.subtitle.json"
    srt_path = target_dir / f"{base}.srt"
    md_path = target_dir / f"{base}.md"

    json_path.write_text(json.dumps({"video": video, "subtitle": picked, "body": body}, ensure_ascii=False, indent=2), encoding="utf-8")
    srt_path.write_text(body_to_srt(body), encoding="utf-8")
    md_path.write_text(body_to_markdown(video, picked, body), encoding="utf-8")

    selected = {"json": json_path, "srt": srt_path, "md": md_path}[fmt]
    return {
        "video": {"title": video["title"], "bvid": video["bvid"], "aid": aid, "cid": cid},
        "subtitle": picked,
        "paths": {"json": str(json_path), "srt": str(srt_path), "md": str(md_path)},
        "selected": str(selected),
    }
