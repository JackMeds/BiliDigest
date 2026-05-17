import json
import time
from pathlib import Path
from typing import Any, Callable

from .bili_client import BiliClient, OUTPUT_DIR
from .bili_library import watch_later, write_jsonl


CACHE_DIR = OUTPUT_DIR / "bilidigest" / "cache"
STATE_DIR = OUTPUT_DIR / "bilidigest" / "state"
DEFAULT_CACHE_TTL_SECONDS = 24 * 60 * 60


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def unique_by_bvid(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for item in items:
        bvid = str(item.get("bvid") or "")
        if not bvid or bvid in seen:
            continue
        seen.add(bvid)
        result.append(item)
    return result


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    items: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                items.append(json.loads(line))
    return items


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def save_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def cache_paths(source: str) -> tuple[Path, Path]:
    return CACHE_DIR / f"{source}.jsonl", CACHE_DIR / f"{source}.meta.json"


def cache_is_usable(meta: dict[str, Any], count: int, limit: int, ttl_seconds: int) -> bool:
    if not meta or count <= 0:
        return False
    fetched_at = float(meta.get("fetched_at_epoch") or 0)
    if ttl_seconds >= 0 and time.time() - fetched_at > ttl_seconds:
        return False
    if count >= limit:
        return True
    return bool(meta.get("exhausted"))


def get_watch_later_items(
    client: BiliClient,
    limit: int,
    *,
    cache_ttl: int = DEFAULT_CACHE_TTL_SECONDS,
    refresh: bool = False,
    progress: Callable[[str], None] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    items_path, meta_path = cache_paths("watch-later")
    cached = unique_by_bvid(read_jsonl(items_path))
    meta = load_json(meta_path)
    if not refresh and cache_is_usable(meta, len(cached), limit, cache_ttl):
        items = cached[:limit]
        return items, {"source": "cache", "path": str(items_path), "meta": str(meta_path), "count": len(items)}

    if progress:
        progress(f"正在刷新稍后再看列表，目标 {limit} 条；这一步会按慢速分页请求。")
    items = unique_by_bvid(watch_later(client, limit))
    path = write_jsonl(items, "watch-later", CACHE_DIR)
    save_json(
        meta_path,
        {
            "source": "watch-later",
            "requested_limit": limit,
            "count": len(items),
            "exhausted": len(items) < limit,
            "fetched_at": now_iso(),
            "fetched_at_epoch": time.time(),
        },
    )
    return items, {"source": "network", "path": str(path), "meta": str(meta_path), "count": len(items)}


def state_path(source: str) -> Path:
    return STATE_DIR / f"{source}.json"


def load_state(source: str) -> dict[str, Any]:
    state = load_json(state_path(source))
    if not state:
        state = {
            "source": source,
            "started_at": now_iso(),
            "updated_at": None,
            "total": 0,
            "completed": {},
            "failed": {},
            "skipped": {},
            "last_error": None,
        }
    state.setdefault("completed", {})
    state.setdefault("failed", {})
    state.setdefault("skipped", {})
    return state


def save_state(source: str, state: dict[str, Any]) -> Path:
    state["updated_at"] = now_iso()
    path = state_path(source)
    save_json(path, state)
    return path

