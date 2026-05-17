import json
from pathlib import Path
from typing import Any

from .bili_client import BiliClient, BiliError, dated_output_dir


def int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def normalize_video(item: dict[str, Any], source: str) -> dict[str, Any]:
    return {
        "source": source,
        "title": item.get("title") or item.get("name") or "Untitled",
        "bvid": item.get("bvid") or item.get("bv_id") or "",
        "aid": item.get("aid") or item.get("id"),
        "cid": item.get("cid"),
        "duration": item.get("duration", 0),
        "pubtime": item.get("pubdate") or item.get("pubtime") or item.get("ctime"),
        "url": f"https://www.bilibili.com/video/{item.get('bvid') or item.get('bv_id')}",
        "raw": item,
    }


def watch_later_with_total(client: BiliClient, limit: int = 15) -> dict[str, Any]:
    videos: list[dict[str, Any]] = []
    page = 1
    total: int | None = None
    while len(videos) < limit:
        body = client.request_json(
            "https://api.bilibili.com/x/v2/history/toview/web",
            {"ps": min(20, limit - len(videos)), "pn": page},
            auth_required=True,
        )
        data = body.get("data") or {}
        if total is None:
            total = int_or_none(data.get("count") or data.get("total"))
        items = (data.get("list") or [])
        if not items:
            break
        videos.extend(normalize_video(item, "watch-later") for item in items)
        if len(items) < 20:
            break
        page += 1
    return {"items": videos[:limit], "total": total}


def watch_later(client: BiliClient, limit: int = 15) -> list[dict[str, Any]]:
    return watch_later_with_total(client, limit)["items"]


def favorite_folders_with_total(client: BiliClient, mid: str | int = "me") -> dict[str, Any]:
    up_mid = client.my_mid() if str(mid) == "me" else int(mid)
    body = client.request_json(
        "https://api.bilibili.com/x/v3/fav/folder/created/list-all",
        {"up_mid": up_mid},
        auth_required=True,
    )
    data = body.get("data") or {}
    items = data.get("list") or []
    return {"items": items, "total": int_or_none(data.get("count")) or len(items)}


def favorite_folders(client: BiliClient, mid: str | int = "me") -> list[dict[str, Any]]:
    return favorite_folders_with_total(client, mid)["items"]


def favorite_items_with_total(client: BiliClient, media_id: int, limit: int = 15) -> dict[str, Any]:
    videos: list[dict[str, Any]] = []
    page = 1
    total: int | None = None
    while len(videos) < limit:
        body = client.request_json(
            "https://api.bilibili.com/x/v3/fav/resource/list",
            {
                "media_id": media_id,
                "pn": page,
                "ps": min(36, limit - len(videos)),
                "platform": "web",
            },
            auth_required=True,
        )
        data = body.get("data") or {}
        if total is None:
            info = data.get("info") or {}
            total = int_or_none(info.get("media_count") or data.get("total") or data.get("count"))
        items = data.get("medias") or []
        if not items:
            break
        videos.extend(normalize_video(item, f"favorite:{media_id}") for item in items)
        if len(items) < 36:
            break
        page += 1
    return {"items": videos[:limit], "total": total}


def favorite_items(client: BiliClient, media_id: int, limit: int = 15) -> list[dict[str, Any]]:
    return favorite_items_with_total(client, media_id, limit)["items"]


def write_jsonl(items: list[dict[str, Any]], name: str, out_dir: Path | None = None) -> Path:
    target_dir = out_dir or dated_output_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / f"{name}.jsonl"
    with path.open("w", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    return path
