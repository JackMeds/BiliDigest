import json
import os
import re
import sqlite3
from pathlib import Path
from urllib.parse import urlparse, parse_qs, urljoin

import requests

from ..bili_client import BiliClient, BiliError, LoginRequired, RiskControl, save_cookies
from ..bili_library import favorite_items_with_total, watch_later_with_total
from .store import AgentError


def safe_url(url, *, media=False):
    try:
        p = urlparse(url)
        port = p.port
    except ValueError:
        raise AgentError("INVALID_URL", "Malformed URL")
    suffixes = ("bilibili.com", "b23.tv")
    if media:
        suffixes += ("bilivideo.com", "bilivideo.cn", "hdslb.com")
    host = (p.hostname or "").lower()
    if p.scheme != "https" or p.username or p.password or port not in (None, 443) or not any(host == s or host.endswith("." + s) for s in suffixes):
        raise AgentError("INVALID_URL", "Only HTTPS Bilibili resources and approved media hosts are supported")
    return url


def public_get(url, *, headers=None):
    # Never forward the authenticated API client's cookie jar to media or redirect hosts.
    base = {"User-Agent": "Mozilla/5.0", "Referer": "https://www.bilibili.com/", **(headers or {})}
    for _ in range(6):
        safe_url(url, media=True)
        response = requests.get(url, headers=base, stream=True, allow_redirects=False, timeout=(15, 60))
        if response.status_code in (301, 302, 303, 307, 308):
            location = response.headers.get("Location", "")
            response.close()
            url = urljoin(url, location)
            continue
        if response.status_code in (412, 429):
            response.close()
            raise RiskControl("Media requests blocked; retry after resolving the platform challenge")
        return response
    raise AgentError("INVALID_URL", "Too many redirects")


def resource_ref(source):
    source = source.strip()
    if source == "watch-later":
        return "watch-later", None
    if re.fullmatch(r"BV[0-9A-Za-z]{10}", source):
        return "video", source
    if re.fullmatch(r"av\d+", source, re.I):
        return "av", source[2:]
    if re.fullmatch(r"(?:mid|fav):\d+", source):
        kind, value = source.split(":")
        return ("uploads" if kind == "mid" else "favorite"), value
    safe_url(source)
    p = urlparse(source)
    if p.hostname == "b23.tv":
        with public_get(source) as response:
            response.raise_for_status()
            return resource_ref(response.url)
    bv = re.search(r"/video/(BV[0-9A-Za-z]{10})", p.path)
    if bv:
        return "video", bv[1]
    av = re.search(r"/video/av(\d+)", p.path)
    if av:
        return "av", av[1]
    if p.hostname == "space.bilibili.com":
        fid = parse_qs(p.query).get("fid")
        if fid and fid[0].isdigit():
            return "favorite", fid[0]
        match = re.fullmatch(r"/(\d+)(?:/(?:upload/video|video))?/?", p.path)
        if match:
            return "uploads", match[1]
    raise AgentError("UNSUPPORTED_RESOURCE", "Use a video, UP space, favorite folder, mid:UID, fav:FID or watch-later")


def video_metadata(client, bvid):
    raw = client.request_json("https://api.bilibili.com/x/web-interface/view", {"bvid": bvid})["data"]
    return {k: raw.get(k) for k in ("bvid", "aid", "title", "desc", "duration", "pubdate", "owner", "pages")}


def discover(client, source, limit=1000):
    if not 1 <= limit <= 10000:
        raise AgentError("INVALID_INPUT", "limit must be between 1 and 10000")
    kind, value = resource_ref(source)
    items, total, exhausted = [], None, False
    if kind in ("video", "av"):
        params = {"bvid" if kind == "video" else "aid": value}
        raw = client.request_json("https://api.bilibili.com/x/web-interface/view", params)["data"]
        items = [{k: raw.get(k) for k in ("bvid", "aid", "title", "duration", "pubdate")}]
        total, exhausted = 1, True
    elif kind in ("watch-later", "favorite"):
        result = watch_later_with_total(client, limit) if kind == "watch-later" else favorite_items_with_total(client, int(value), limit)
        items = [{k: i.get(k) for k in ("bvid", "aid", "title", "duration", "pubtime")} for i in result["items"]]
        total = result["total"]
        exhausted = len(items) < limit
    else:
        seen = set()
        pn = 1
        while len(items) < limit:
            data = client.request_json("https://api.bilibili.com/x/space/wbi/arc/search", {"mid": int(value), "pn": pn, "ps": 50, "order": "pubdate"}, wbi=True)["data"]
            total = (data.get("page") or {}).get("count")
            batch = (data.get("list") or {}).get("vlist") or []
            previous = len(items)
            for row in batch:
                bv = row.get("bvid")
                if not bv or bv in seen or len(items) >= limit:
                    continue
                seen.add(bv)
                length = row.get("length", "0")
                duration = 0
                for number in str(length).split(":"):
                    duration = duration * 60 + int(number)
                items.append({"bvid": bv, "aid": row.get("aid"), "title": row["title"], "duration": duration, "pubdate": row.get("created"), "description": row.get("description", "")})
            if not batch:
                exhausted = True
                break
            if len(items) == previous:
                break
            if total is not None and len(items) >= total:
                exhausted = True
                break
            pn += 1
    unique = {i["bvid"]: {**i, "url": f'https://www.bilibili.com/video/{i["bvid"]}'} for i in items if i.get("bvid")}
    complete = len(unique) >= total if total is not None else exhausted
    return {"source": source, "kind": kind, "remote_total": total, "fetched_count": len(unique), "complete": complete, "items": list(unique.values())}


def import_bilitools(path=None, session_path=None):
    path = Path(path or os.getenv("BILITOOLS_DATABASE", Path.home() / "Library/Application Support/com.btjawa.bilitools/Storage")).expanduser().resolve()
    if not path.is_file():
        raise AgentError("AUTH_SOURCE_MISSING", "BiliTools database not found; use --database or QR login")
    with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True) as db:
        rows = db.execute("SELECT name,value,domain FROM cookies").fetchall()
    cookies = {name: value for name, value, domain in rows if not domain or domain.lstrip(".") == "bilibili.com" or domain.endswith(".bilibili.com")}
    if not cookies:
        raise AgentError("AUTH_REQUIRED", "No Bilibili session found in BiliTools")
    profile = BiliClient(cookies=cookies).login_status()
    save_cookies(cookies, session_path)
    return {"status": "logged_in", "mid": profile.get("mid"), "source": "bilitools"}
