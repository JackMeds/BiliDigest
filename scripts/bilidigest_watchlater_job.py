#!/usr/bin/env python3
"""Stable Watch Later runner for Hermes and local automation.

This script keeps Hermes out of command-planning details. It pins the working
directory, Python module entrypoint, locking, logging, and auth checks before
delegating the actual BiliDigest work to ``python -m tools.bilidigest``.
"""

from __future__ import annotations

import argparse
import contextlib
import fcntl
import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import bili_paths  # noqa: E402

LOG_DIR = bili_paths.LOG_DIR
STATE_PATH = bili_paths.batch_state_dir() / "watch-later.json"
SESSION_PATH = bili_paths.SESSION_FILE
LOCK_PATH = bili_paths.stable_lock_path()


def resolve_python() -> str:
    explicit = os.environ.get("BILIDIGEST_PYTHON")
    if explicit:
        return explicit
    local_venv = ROOT / ".venv" / "bin" / "python"
    if local_venv.exists():
        return str(local_venv)
    return shutil.which("python") or sys.executable


BILIDIGEST_PYTHON = resolve_python()


class JobError(RuntimeError):
    def __init__(self, message: str, code: int = 1) -> None:
        super().__init__(message)
        self.code = code


@dataclass
class CommandResult:
    args: list[str]
    returncode: int
    stdout: str
    stderr: str
    elapsed: float


class Tee:
    def __init__(self, log_path: Path) -> None:
        self.log_path = log_path
        log_path.parent.mkdir(parents=True, exist_ok=True)
        self._file = log_path.open("a", encoding="utf-8")

    def close(self) -> None:
        self._file.close()

    def write(self, message: str = "") -> None:
        text = message.rstrip("\n")
        print(text, flush=True)
        self._file.write(text + "\n")
        self._file.flush()

    def section(self, title: str) -> None:
        self.write("")
        self.write(f"== {title} ==")


def now_stamp() -> str:
    return time.strftime("%Y%m%d-%H%M%S")


def parse_json(text: str) -> dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {}


def run_cli(args: list[str], *, timeout: int, tee: Tee, ok: tuple[int, ...] = (0,)) -> CommandResult:
    cmd = [BILIDIGEST_PYTHON, "-m", "tools.bilidigest", *args]
    started = time.time()
    tee.write(f"$ cd {ROOT} && {' '.join(cmd)}")
    try:
        proc = subprocess.run(
            cmd,
            cwd=ROOT,
            env={**os.environ, "PYTHONUNBUFFERED": "1"},
            text=True,
            capture_output=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
        if stdout:
            tee.write(stdout.rstrip())
        if stderr:
            tee.write(stderr.rstrip())
        raise JobError(f"Command timed out after {timeout}s: {' '.join(cmd)}", code=124) from exc

    elapsed = time.time() - started
    if proc.stdout:
        tee.write(proc.stdout.rstrip())
    if proc.stderr:
        tee.write(proc.stderr.rstrip())
    tee.write(f"[exit={proc.returncode} elapsed={elapsed:.1f}s]")
    result = CommandResult(cmd, proc.returncode, proc.stdout, proc.stderr, elapsed)
    if proc.returncode not in ok:
        raise JobError(f"Command failed: {' '.join(cmd)}", code=proc.returncode)
    return result


@contextlib.contextmanager
def job_lock() -> Any:
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOCK_PATH.open("w", encoding="utf-8") as lock_file:
        try:
            fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise JobError(f"Another BiliDigest job is already running: {LOCK_PATH}", code=75) from exc
        lock_file.write(f"pid={os.getpid()} started_at={time.strftime('%Y-%m-%dT%H:%M:%S')}\n")
        lock_file.flush()
        try:
            yield
        finally:
            fcntl.flock(lock_file, fcntl.LOCK_UN)


def load_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        return {}
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def summarize_state(state: dict[str, Any]) -> dict[str, Any]:
    completed = state.get("completed") if isinstance(state.get("completed"), dict) else {}
    failed = state.get("failed") if isinstance(state.get("failed"), dict) else {}
    skipped = state.get("skipped") if isinstance(state.get("skipped"), dict) else {}
    cache = state.get("cache") if isinstance(state.get("cache"), dict) else {}
    return {
        "state_path": str(STATE_PATH),
        "output_dir": state.get("output_dir"),
        "updated_at": state.get("updated_at"),
        "limit": state.get("limit"),
        "total_in_run": state.get("total"),
        "completed": len(completed),
        "failed": len(failed),
        "skipped": len(skipped),
        "cache_source": cache.get("source"),
        "remote_total": cache.get("total"),
        "last_error": state.get("last_error"),
    }


def auth_status(tee: Tee) -> dict[str, Any]:
    result = run_cli(["auth", "status", "--json"], timeout=60, tee=tee, ok=(0, 1))
    payload = parse_json(result.stdout)
    if not payload:
        payload = {"status": "unknown", "raw": result.stdout.strip() or result.stderr.strip()}
    return payload


def ensure_auth(args: argparse.Namespace, tee: Tee) -> dict[str, Any]:
    tee.section("Bilibili Auth")
    status = auth_status(tee)
    if status.get("status") == "logged_in":
        return status

    if args.import_browser:
        tee.write(f"Trying browser cookie import: {args.import_browser}")
        run_cli(["auth", "import-browser", args.import_browser, "--json"], timeout=180, tee=tee, ok=(0, 1))
        status = auth_status(tee)
        if status.get("status") == "logged_in":
            return status

    if args.qr:
        tee.write("Creating non-blocking QR login request.")
        result = run_cli(["auth", "login", "--json", "--no-wait"], timeout=60, tee=tee)
        payload = parse_json(result.stdout)
        if payload:
            raise JobError(
                "Bilibili login is required. Scan the QR/login URL, then run "
                f"`{Path(__file__).name} poll {payload.get('qrcode_key')}`. "
                f"QR image: {payload.get('qr_image')}",
                code=10,
            )

    raise JobError(
        "Bilibili login is required. Fastest recovery: run "
        f"`{Path(__file__)} login --import-browser edge --qr` or "
        "`python -m tools.bilidigest auth login --json --no-wait`.",
        code=10,
    )


def cmd_doctor(args: argparse.Namespace, tee: Tee) -> int:
    tee.section("Runtime")
    tee.write(f"root={ROOT}")
    tee.write(f"script_python={sys.executable}")
    tee.write(f"bilidigest_python={BILIDIGEST_PYTHON}")
    tee.write(f"data_dir={bili_paths.DATA_DIR}")
    tee.write(f"cache_dir={bili_paths.CACHE_DIR}")
    tee.write(f"log_dir={bili_paths.LOG_DIR}")
    tee.write(f"output_dir={bili_paths.OUTPUT_DIR}")
    tee.write(f"session={SESSION_PATH} exists={SESSION_PATH.exists()}")
    tee.write(f"state={STATE_PATH} exists={STATE_PATH.exists()}")
    tee.write(f"lock={LOCK_PATH}")
    tee.write(f"log={tee.log_path}")
    auth_status(tee)
    tee.section("State")
    tee.write(json.dumps(summarize_state(load_state()), ensure_ascii=False, indent=2))
    return 0


def cmd_login(args: argparse.Namespace, tee: Tee) -> int:
    tee.section("Bilibili Auth")
    status = auth_status(tee)
    if status.get("status") == "logged_in":
        tee.write("Bilibili auth is ready.")
        return 0
    if args.import_browser:
        tee.write(f"Trying browser cookie import: {args.import_browser}")
        run_cli(["auth", "import-browser", args.import_browser, "--json"], timeout=180, tee=tee, ok=(0, 1))
        status = auth_status(tee)
        if status.get("status") == "logged_in":
            tee.write("Bilibili auth is ready.")
            return 0
    if args.qr:
        result = run_cli(["auth", "login", "--json", "--no-wait"], timeout=60, tee=tee)
        payload = parse_json(result.stdout)
        tee.write(
            "QR login created. Scan it, then poll with: "
            f"{Path(__file__).name} poll {payload.get('qrcode_key')}"
        )
        return 0
    raise JobError(
        "Bilibili login is required. Run this command with `--import-browser edge --qr`.",
        code=10,
    )


def cmd_poll(args: argparse.Namespace, tee: Tee) -> int:
    tee.section("Poll Login")
    run_cli(["auth", "poll", args.qrcode_key, "--json"], timeout=60, tee=tee)
    return 0


def cmd_run(args: argparse.Namespace, tee: Tee) -> int:
    with job_lock():
        ensure_auth(args, tee)
        before = summarize_state(load_state())
        tee.section("Before")
        tee.write(json.dumps(before, ensure_ascii=False, indent=2))

        batch = ["batch", "watch-later", "--limit", str(args.limit), "--fallback-summary", "--with-summary"]
        if args.refresh_list:
            batch.append("--refresh-list")
        if args.only_new:
            batch.append("--only-new")
        if args.no_resume:
            batch.append("--no-resume")
        if args.retry_failed:
            batch.append("--retry-failed")

        tee.section("Batch")
        run_cli(batch, timeout=args.timeout, tee=tee)

        after = summarize_state(load_state())
        tee.section("After")
        tee.write(json.dumps(after, ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Stable BiliDigest Watch Later automation entrypoint")
    parser.add_argument("--log", help="Override log path")
    sub = parser.add_subparsers(dest="command", required=True)

    doctor = sub.add_parser("doctor", help="Check runtime, auth, and persisted state")
    doctor.set_defaults(func=cmd_doctor)

    login = sub.add_parser("login", help="Prepare Bilibili auth without running a batch")
    login.add_argument("--import-browser", choices=["edge", "chrome", "safari", "firefox"], default=None)
    login.add_argument("--qr", action="store_true", help="Create non-blocking QR login if browser import fails")
    login.set_defaults(func=cmd_login)

    poll = sub.add_parser("poll", help="Poll a non-blocking QR login key")
    poll.add_argument("qrcode_key")
    poll.set_defaults(func=cmd_poll)

    run = sub.add_parser("run", help="Run the resumable Watch Later batch")
    run.add_argument("--limit", type=int, default=600)
    run.add_argument("--timeout", type=int, default=6 * 60 * 60)
    run.add_argument("--refresh-list", action=argparse.BooleanOptionalAction, default=True)
    run.add_argument("--only-new", action=argparse.BooleanOptionalAction, default=True)
    run.add_argument("--no-resume", action="store_true")
    run.add_argument("--retry-failed", action="store_true")
    run.add_argument("--import-browser", choices=["edge", "chrome", "safari", "firefox"], default=None)
    run.add_argument("--qr", action="store_true", help="Create non-blocking QR login if not logged in")
    run.set_defaults(func=cmd_run)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    log_path = Path(args.log) if args.log else LOG_DIR / f"stable-watchlater-{now_stamp()}.log"
    tee = Tee(log_path)
    try:
        tee.write(f"BiliDigest stable job started at {time.strftime('%Y-%m-%dT%H:%M:%S')}")
        return int(args.func(args, tee))
    except JobError as exc:
        tee.write(f"ERROR: {exc}")
        return exc.code
    finally:
        tee.write(f"BiliDigest stable job finished at {time.strftime('%Y-%m-%dT%H:%M:%S')}")
        tee.close()


if __name__ == "__main__":
    raise SystemExit(main())
