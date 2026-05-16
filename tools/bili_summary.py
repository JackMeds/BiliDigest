from pathlib import Path
from typing import Any

from .bili_client import BiliClient, BiliError, dated_output_dir, sanitize_filename


def duration(seconds: int) -> str:
    minutes, secs = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def summary_to_markdown(video: dict[str, Any], result: dict[str, Any]) -> str:
    lines = [
        f"# {video['title']} - B站 AI 总结",
        "",
        f"- BV: {video['bvid']}",
        f"- URL: https://www.bilibili.com/video/{video['bvid']}",
        "",
        result.get("summary", "").strip(),
        "",
    ]
    for section in result.get("outline") or []:
        ts = int(section.get("timestamp") or 0)
        lines.append(f"## {section.get('title', '片段')} - [{duration(ts)}](https://www.bilibili.com/video/{video['bvid']}?t={ts})")
        lines.append("")
        for part in section.get("part_outline") or []:
            pts = int(part.get("timestamp") or 0)
            lines.append(f"- {part.get('content', '').strip()} - [{duration(pts)}](https://www.bilibili.com/video/{video['bvid']}?t={pts})")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def export_summary(client: BiliClient, value: str, out_dir: Path | None = None) -> dict[str, Any]:
    video = client.video_info(value)
    pages = video.get("pages") or []
    if not pages:
        raise BiliError("Video has no playable pages")
    page = pages[0]
    body = client.request_json(
        "https://api.bilibili.com/x/web-interface/view/conclusion/get",
        {"aid": int(video["aid"]), "cid": int(page["cid"])},
        wbi=True,
        auth_required=True,
        ignore_error=True,
    )
    if body.get("code") != 0:
        raise BiliError(body.get("message") or "Bilibili AI summary is unavailable", code=body.get("code"))
    result = ((body.get("data") or {}).get("model_result") or {})
    if not result.get("result_type"):
        raise BiliError("Bilibili AI summary is unavailable for this video")
    target_dir = out_dir or dated_output_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / f"{sanitize_filename(video['title'])}-{video['bvid']}.summary.md"
    path.write_text(summary_to_markdown(video, result), encoding="utf-8")
    return {"path": str(path), "video": {"title": video["title"], "bvid": video["bvid"]}}
