import os
import platform
import time
from pathlib import Path


ROOT_DIR = Path(__file__).parent.parent.resolve()
LEGACY_OUTPUT_DIR = ROOT_DIR / "output"
LEGACY_SESSION_FILE = ROOT_DIR / ".user_session.json"


def _env_path(name: str) -> Path | None:
    value = os.environ.get(name)
    return Path(value).expanduser() if value else None


def _mac_or_xdg_dir(kind: str, app_name: str = "BiliDigest") -> Path:
    if platform.system() == "Windows":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / app_name
        return base / {"data": "data", "cache": "cache", "log": "logs"}[kind]
    if platform.system() == "Darwin":
        if kind == "data":
            return Path.home() / "Library" / "Application Support" / app_name
        if kind == "cache":
            return Path.home() / "Library" / "Caches" / app_name
        if kind == "log":
            return Path.home() / "Library" / "Logs" / app_name
    if kind == "data":
        root = os.environ.get("XDG_DATA_HOME")
        return Path(root).expanduser() / app_name.lower() if root else Path.home() / ".local" / "share" / app_name.lower()
    if kind == "cache":
        root = os.environ.get("XDG_CACHE_HOME")
        return Path(root).expanduser() / app_name.lower() if root else Path.home() / ".cache" / app_name.lower()
    if kind == "log":
        root = os.environ.get("XDG_STATE_HOME")
        return Path(root).expanduser() / app_name.lower() / "logs" if root else Path.home() / ".local" / "state" / app_name.lower() / "logs"
    raise ValueError(f"Unknown path kind: {kind}")


def _documents_dir() -> Path:
    return Path.home() / "Documents" / "BiliDigest"


DATA_DIR = _env_path("BILIDIGEST_DATA_DIR") or _mac_or_xdg_dir("data")
CACHE_DIR = _env_path("BILIDIGEST_CACHE_DIR") or _mac_or_xdg_dir("cache")
LOG_DIR = _env_path("BILIDIGEST_LOG_DIR") or _mac_or_xdg_dir("log")
OUTPUT_DIR = _env_path("BILIDIGEST_OUTPUT_DIR") or _documents_dir()

OLD_DATA_DIR = (
    Path.home() / "Library" / "Application Support" / "BiliSubNotes"
    if platform.system() == "Darwin"
    else Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")).expanduser() / "bilisubnotes"
)

SESSION_FILE = DATA_DIR / "session.json"
OLD_APP_SESSION_FILE = OLD_DATA_DIR / "session.json"
QR_IMAGE_PATH = CACHE_DIR / "login_qr.png"


def dated_output_dir(date: str | None = None) -> Path:
    out_dir = OUTPUT_DIR / "bilidigest" / (date or time.strftime("%Y-%m-%d"))
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def batch_cache_dir() -> Path:
    return CACHE_DIR / "bilidigest" / "cache"


def batch_snapshot_dir() -> Path:
    return CACHE_DIR / "bilidigest" / "snapshots"


def batch_state_dir() -> Path:
    return DATA_DIR / "state"


def stable_lock_path() -> Path:
    return batch_state_dir() / "watch-later.lock"


def stable_log_path(filename: str) -> Path:
    return LOG_DIR / filename


def reports_dir() -> Path:
    return OUTPUT_DIR / "bilidigest" / "reports"


def site_dir() -> Path:
    return OUTPUT_DIR / "bilidigest" / "site"


def legacy_output_dir() -> Path:
    return OUTPUT_DIR / "legacy-output"
