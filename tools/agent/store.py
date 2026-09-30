import hashlib
import json
import os
import re
import sqlite3
import time
import uuid
from pathlib import Path

from filelock import FileLock

from .. import bili_paths


class AgentError(Exception):
    def __init__(self, code, message, *, retryable=False):
        super().__init__(message)
        self.code, self.retryable = code, retryable

    def payload(self):
        return {"code": self.code, "message": str(self), "retryable": self.retryable}


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        with temp.open("w", encoding="utf-8") as f:
            json.dump(value, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        temp.replace(path)
    finally:
        temp.unlink(missing_ok=True)


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def valid_id(value):
    if not re.fullmatch(r"[0-9a-f]{32}", str(value)):
        raise AgentError("INVALID_ID", "Expected a BiliDigest resource ID")
    return value


class Store:
    def __init__(self, data_dir=None, output_dir=None):
        self.root = Path(data_dir or bili_paths.DATA_DIR).expanduser().resolve() / "agent"
        self.output = Path(output_dir or bili_paths.OUTPUT_DIR).expanduser().resolve() / "jobs"
        self.root.mkdir(parents=True, exist_ok=True)
        self.output.mkdir(parents=True, exist_ok=True)
        self.db_path = self.root / "jobs.sqlite3"
        with self.connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, idem TEXT UNIQUE, plan_id TEXT NOT NULL, state TEXT NOT NULL, cancel INTEGER NOT NULL DEFAULT 0, payload TEXT NOT NULL, updated REAL NOT NULL)")

    def connect(self):
        db = sqlite3.connect(self.db_path, timeout=30)
        db.row_factory = sqlite3.Row
        return db

    def lock(self, job_id):
        return FileLock(str(self.root / (valid_id(job_id) + ".lock")))

    def save_resource(self, kind, value):
        resource_id = uuid.uuid4().hex
        value = {**value, "id": resource_id, "created_at": time.time()}
        atomic_json(self.root / kind / (resource_id + ".json"), value)
        return value

    def resource(self, kind, resource_id):
        path = self.root / kind / (valid_id(resource_id) + ".json")
        if not path.is_file():
            raise AgentError("NOT_FOUND", f"{kind} resource not found")
        return json.loads(path.read_text(encoding="utf-8"))

    def create_job(self, plan_id, idempotency_key=None):
        plan = self.resource("plans", plan_id)
        job_id = uuid.uuid4().hex
        payload = {"id": job_id, "plan_id": plan_id, "state": "queued", "created_at": time.time(), "parts": {}, "errors": [], "artifacts": [], "video_count": len(plan["items"])}
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if idempotency_key:
                row = db.execute("SELECT * FROM jobs WHERE idem=?", (idempotency_key,)).fetchone()
                if row:
                    if row["plan_id"] != plan_id:
                        raise AgentError("IDEMPOTENCY_CONFLICT", "This key already belongs to a different plan")
                    return self._decode(row), False
            db.execute("INSERT INTO jobs VALUES (?,?,?,?,?,?,?)", (job_id, idempotency_key, plan_id, "queued", 0, json.dumps(payload, ensure_ascii=False), time.time()))
        return payload, True

    def _decode(self, row):
        value = json.loads(row["payload"])
        value.update(state=row["state"], cancel_requested=bool(row["cancel"]), updated_at=row["updated"])
        return value

    def job(self, job_id):
        with self.connect() as db:
            row = db.execute("SELECT * FROM jobs WHERE id=?", (valid_id(job_id),)).fetchone()
        if not row:
            raise AgentError("NOT_FOUND", "Job not found")
        return self._decode(row)

    def jobs(self):
        with self.connect() as db:
            rows = db.execute("SELECT * FROM jobs ORDER BY updated DESC LIMIT 100").fetchall()
        return [{k: self._decode(row).get(k) for k in ("id", "plan_id", "state", "updated_at", "video_count")} for row in rows]

    def save_job(self, job, state=None):
        # Cancellation has a separate column, so a worker cannot overwrite a newer cancel request.
        with self.connect() as db:
            db.execute("UPDATE jobs SET state=?,payload=?,updated=? WHERE id=?", (state or job["state"], json.dumps(job, ensure_ascii=False), time.time(), job["id"]))

    def cancel(self, job_id):
        self.job(job_id)
        with self.connect() as db:
            db.execute("UPDATE jobs SET cancel=1,state=CASE WHEN state='queued' THEN 'cancelled' ELSE state END,updated=? WHERE id=?", (time.time(), job_id))
        return self.job(job_id)

    def requeue(self, job_id):
        with self.connect() as db:
            db.execute("UPDATE jobs SET state='queued',cancel=0,updated=? WHERE id=?", (time.time(), valid_id(job_id)))

    def job_dir(self, job_id):
        path = self.output / valid_id(job_id)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def cancelled(self, job_id):
        with self.connect() as db:
            row = db.execute("SELECT cancel FROM jobs WHERE id=?", (job_id,)).fetchone()
        return bool(row and row[0])
