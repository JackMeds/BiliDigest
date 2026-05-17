import hashlib
import json
import os
import platform
import random
import re
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import requests


ROOT_DIR = Path(__file__).parent.parent.resolve()
LEGACY_SESSION_FILE = ROOT_DIR / ".user_session.json"
OUTPUT_DIR = ROOT_DIR / "output"
DEFAULT_DELAY_SECONDS = float(os.environ.get("BILIDIGEST_DELAY_SECONDS", os.environ.get("BILISUB_DELAY_SECONDS", "8.0")))
DEFAULT_DELAY_JITTER_SECONDS = float(os.environ.get("BILIDIGEST_DELAY_JITTER_SECONDS", os.environ.get("BILISUB_DELAY_JITTER_SECONDS", "4.0")))
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36"
)


def user_data_dir() -> Path:
    if platform.system() == "Darwin":
        return Path.home() / "Library" / "Application Support" / "BiliDigest"
    root = os.environ.get("XDG_DATA_HOME")
    return Path(root).expanduser() / "bilidigest" if root else Path.home() / ".local" / "share" / "bilidigest"


def old_user_data_dir() -> Path:
    if platform.system() == "Darwin":
        return Path.home() / "Library" / "Application Support" / "BiliSubNotes"
    root = os.environ.get("XDG_DATA_HOME")
    return Path(root).expanduser() / "bilisubnotes" if root else Path.home() / ".local" / "share" / "bilisubnotes"


SESSION_FILE = user_data_dir() / "session.json"
OLD_APP_SESSION_FILE = old_user_data_dir() / "session.json"


class BiliError(RuntimeError):
    def __init__(self, message: str, code: int | str | None = None, stop_batch: bool = False):
        super().__init__(message)
        self.code = code
        self.stop_batch = stop_batch


class LoginRequired(BiliError):
    def __init__(self, message: str = "Bilibili session is missing or expired"):
        super().__init__(message, code=-101, stop_batch=True)


class RiskControl(BiliError):
    def __init__(self, message: str = "Bilibili risk control was triggered"):
        super().__init__(message, code=412, stop_batch=True)


def load_cookies(path: Path | None = None) -> dict[str, str]:
    session_path = path or SESSION_FILE
    if not session_path.exists() and path is None:
        for legacy_path in (OLD_APP_SESSION_FILE, LEGACY_SESSION_FILE):
            cookies = _read_cookie_json(legacy_path)
            if cookies:
                save_cookies(cookies)
                return cookies
    return _read_cookie_json(session_path)


def _read_cookie_json(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(k): str(v) for k, v in data.items() if v is not None}


def save_cookies(cookies: dict[str, str], path: Path | None = None) -> None:
    session_path = path or SESSION_FILE
    session_path.parent.mkdir(parents=True, exist_ok=True)
    session_path.write_text(json.dumps(cookies, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        session_path.chmod(0o600)
    except OSError:
        pass


def sanitize_filename(value: str, max_len: int = 90) -> str:
    text = re.sub(r"[\u0000-\u001f\u007f/\\:*?\"<>|]+", "_", value).strip(" ._")
    return (text or "untitled")[:max_len]


def dated_output_dir() -> Path:
    out_dir = OUTPUT_DIR / "bilidigest" / time.strftime("%Y-%m-%d")
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


class BiliClient:
    def __init__(self, cookies: dict[str, str] | None = None, delay: float | None = None):
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": USER_AGENT,
                "Referer": "https://www.bilibili.com/",
                "Origin": "https://www.bilibili.com",
            }
        )
        self.session.cookies.update(cookies if cookies is not None else load_cookies())
        self.delay = DEFAULT_DELAY_SECONDS if delay is None else delay
        self.delay_jitter = 0.0 if self.delay == 0 else DEFAULT_DELAY_JITTER_SECONDS
        self._last_request = 0.0
        self._wbi_key: str | None = None

    @property
    def cookies(self) -> dict[str, str]:
        return self.session.cookies.get_dict()

    def throttle(self) -> None:
        elapsed = time.time() - self._last_request
        wait = self.delay + random.uniform(0.0, self.delay_jitter) - elapsed
        if wait > 0:
            time.sleep(wait)
        self._last_request = time.time()

    def request_json(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        *,
        wbi: bool = False,
        auth_required: bool = False,
        ignore_error: bool = False,
        timeout: int = 15,
    ) -> dict[str, Any]:
        if auth_required and not self.cookies:
            raise LoginRequired()
        self.throttle()
        signed_params = self.sign_wbi(params or {}) if wbi else (params or {})
        resp = self.session.get(url, params=signed_params, timeout=timeout)
        if resp.status_code == 412:
            raise RiskControl("HTTP 412 Precondition Failed: request paused for account safety")
        resp.raise_for_status()
        body = resp.json()
        code = body.get("code", 0)
        if code == 0 or ignore_error:
            return body
        if code == -101:
            raise LoginRequired(body.get("message") or "Bilibili login required")
        if code in {-352, -412}:
            raise RiskControl(body.get("message") or "Bilibili risk control was triggered")
        raise BiliError(body.get("message") or body.get("msg") or f"Bilibili API error {code}", code=code)

    def resolve_url(self, value: str) -> str:
        raw = value.strip()
        if re.match(r"^BV[0-9A-Za-z]{10}$", raw, re.I):
            return f"https://www.bilibili.com/video/{raw}"
        if raw.startswith("http://") or raw.startswith("https://"):
            self.throttle()
            resp = self.session.get(raw, allow_redirects=True, timeout=15)
            if resp.status_code == 412:
                raise RiskControl()
            resp.raise_for_status()
            return resp.url
        return raw

    def extract_bvid(self, value: str) -> str:
        resolved = self.resolve_url(value)
        match = re.search(r"(BV[0-9A-Za-z]{10})", resolved)
        if not match:
            raise BiliError(f"Cannot find BV id from: {value}")
        return match.group(1)

    def nav(self) -> dict[str, Any]:
        return self.request_json("https://api.bilibili.com/x/web-interface/nav", ignore_error=True)

    def login_status(self) -> dict[str, Any]:
        body = self.nav()
        data = body.get("data") or {}
        if body.get("code") != 0 or not data.get("isLogin"):
            raise LoginRequired("Not logged in or session expired")
        return data

    def my_mid(self) -> int:
        return int(self.login_status()["mid"])

    def video_info(self, value: str) -> dict[str, Any]:
        bvid = self.extract_bvid(value)
        return self.request_json(
            "https://api.bilibili.com/x/web-interface/view",
            {"bvid": bvid},
        )["data"]

    def player_info(self, aid: int, cid: int) -> dict[str, Any]:
        return self.request_json(
            "https://api.bilibili.com/x/player/wbi/v2",
            {"aid": aid, "cid": cid},
            wbi=True,
            auth_required=True,
        )["data"]

    def sign_wbi(self, params: dict[str, Any]) -> dict[str, Any]:
        mixin_key = self._get_wbi_key()
        signed = {k: v for k, v in params.items() if v is not None}
        signed.update(
            {
                "wts": int(time.time()),
                "dm_img_str": "bm8gd2ViZ2",
                "dm_cover_img_str": "bm8gd2ViZ2wgZXh0ZW5zaW",
                "dm_img_list": "[]",
            }
        )
        query = urlencode(
            [
                (k, re.sub(r"[!'()*]", "", str(signed[k])))
                for k in sorted(signed)
            ]
        )
        signed["w_rid"] = hashlib.md5((query + mixin_key).encode("utf-8")).hexdigest()
        return signed

    def _get_wbi_key(self) -> str:
        if self._wbi_key:
            return self._wbi_key
        body = self.nav()
        data = body.get("data") or {}
        wbi_img = data.get("wbi_img") or {}
        img_key = Path(wbi_img.get("img_url", "")).stem
        sub_key = Path(wbi_img.get("sub_url", "")).stem
        if not img_key or not sub_key:
            raise LoginRequired("Cannot fetch WBI keys; login may be expired")
        table = [
            46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35,
            27, 43, 5, 49, 33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13,
            37, 48, 7, 16, 24, 55, 40, 61, 26, 17, 0, 1, 60, 51, 30, 4,
            22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11, 36, 20, 34, 44, 52,
        ]
        source = img_key + sub_key
        self._wbi_key = "".join(source[i] for i in table if i < len(source))[:32]
        return self._wbi_key
