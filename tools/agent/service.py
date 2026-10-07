import csv
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path
from urllib.parse import quote

from filelock import FileLock, Timeout

from ..bili_client import BiliClient, BiliError, LoginRequired, RiskControl, load_cookies
from . import VERSION, media, platform
from .store import AgentError, Store, atomic_json, sha256


def error_payload(exc):
    if isinstance(exc, AgentError):
        return exc.payload()
    if isinstance(exc, LoginRequired):
        return AgentError("AUTH_REQUIRED", "Bilibili login is required; log in and resume").payload()
    if isinstance(exc, RiskControl):
        return AgentError("RISK_BLOCKED", "Bilibili requests are blocked; resolve the challenge before resuming").payload()
    if isinstance(exc, BiliError):
        return AgentError("PLATFORM_ERROR", f"Bilibili API returned error code {exc.code}").payload()
    # Avoid returning signed URLs, cookies or local exception internals over an agent transport.
    return AgentError("OPERATION_FAILED", f"Operation failed ({type(exc).__name__}); retry or inspect local configuration", retryable=True).payload()


class Service:
    def __init__(self, store=None, client=None):
        self.store = store or Store()
        self.client = client or BiliClient(cookies=load_cookies(self.store.root.parent / "session.json"))

    def settings(self):
        config = self.store.root / "settings.json"
        return json.loads(config.read_text(encoding="utf-8")) if config.exists() else {}

    def qwen_model(self):
        return os.getenv("BILIDIGEST_QWEN_MODEL") or self.settings().get("qwen_model")

    def doctor(self):
        from . import qwen_asr
        settings = self.settings()
        backend = settings.get("asr_backend", "whisper-cpp" if self.whisper_model() else "none")
        tools = {name: shutil.which(name) for name in ("ffmpeg", "ffprobe", "whisper-cli")}
        ready = False
        model = None
        if backend == "qwen3-asr":
            model = self.qwen_model()
            try:
                qwen_asr.model_config(model)
                ready = qwen_asr.runtime_ready()
            except AgentError:
                pass
        elif backend == "whisper-cpp":
            model = self.whisper_model()
            ready = bool(model and Path(model).is_file() and tools["whisper-cli"])
        return {"version": VERSION, "python": sys.version.split()[0], "data_dir": str(self.store.root.parent), "output_dir": str(self.store.output.parent), "executables": tools, "media_ready": bool(tools["ffmpeg"] and tools["ffprobe"]), "asr_ready": ready, "asr_backend": backend, "asr_model": model, "qwen_runtime_ready": qwen_asr.runtime_ready(), "timestamp_kind": "chunk_boundaries" if backend == "qwen3-asr" else "model_segments", "http_ready": importlib.util.find_spec("fastapi") is not None, "auth_configured": bool(self.client.cookies), "next_steps": ["Use auth status to validate the session", "Configure a local ASR model if transcription is needed"]}

    def whisper_model(self):
        return os.getenv("BILIDIGEST_WHISPER_MODEL") or self.settings().get("whisper_model")

    def configure(self, whisper_model=None, *, asr_backend=None, asr_model=None):
        from . import qwen_asr
        settings = self.settings()
        if whisper_model:
            if asr_backend or asr_model:
                raise AgentError("INVALID_INPUT", "Use either --whisper-model or --asr-backend/--asr-model")
            asr_backend, asr_model = "whisper-cpp", whisper_model
        if asr_backend == "qwen3-asr":
            path, _ = qwen_asr.model_config(asr_model)
            settings.update(asr_backend=asr_backend, qwen_model=str(path))
            settings.pop("whisper_model", None)
        elif asr_backend == "whisper-cpp":
            path = Path(asr_model or "").expanduser().resolve()
            if not path.is_file():
                raise AgentError("INVALID_MODEL", "The local GGML model file does not exist")
            settings.update(asr_backend=asr_backend, whisper_model=str(path))
        elif asr_backend == "none" and not asr_model:
            settings["asr_backend"] = "none"
        else:
            raise AgentError("INVALID_INPUT", "Select --asr-backend and a local --asr-model")
        atomic_json(self.store.root / "settings.json", settings)
        return {k: settings[k] for k in ("asr_backend", "qwen_model", "whisper_model") if k in settings}

    def auth(self, action="status", value=None):
        if action == "import-bilitools":
            return platform.import_bilitools(value, self.store.root.parent / "session.json")
        if action == "status":
            try:
                profile = self.client.login_status()
                return {"status": "logged_in", "mid": profile.get("mid"), "name": profile.get("uname")}
            except LoginRequired:
                return {"status": "not_logged_in", "next_action": "auth login or auth import-bilitools"}
        from .. import bili_auth
        if action == "login":
            return bili_auth.create_login_request(output_dir=self.store.root / "auth")
        if action == "poll" and value:
            return bili_auth.poll_once(value, session_path=self.store.root.parent / "session.json")
        raise AgentError("INVALID_INPUT", "Use auth status, login, poll or import-bilitools")

    def discover(self, source, limit=1000):
        result = platform.discover(self.client, source, limit)
        snapshot = self.store.save_resource("snapshots", result)
        return {k: v for k, v in snapshot.items() if k != "items"} | {"preview": snapshot["items"][:20]}

    def snapshot(self, resource_id, offset=0, limit=100):
        if offset < 0 or not 1 <= limit <= 1000:
            raise AgentError("INVALID_INPUT", "Invalid pagination range")
        result = self.store.resource("snapshots", resource_id)
        return {**result, "items": result["items"][offset:offset + limit], "offset": offset, "next_offset": offset + limit if offset + limit < len(result["items"]) else None}

    def plan(self, snapshot_id, *, select=None, exclude=None, keywords=None, mode="audio-preferred", asr=None, language="auto", summarize=False, allow_partial=False):
        asr = asr if asr is not None else self.settings().get("asr_backend", "none")
        if mode not in ("audio-preferred", "audio", "video") or asr not in ("none", "whisper-cpp", "qwen3-asr"):
            raise AgentError("INVALID_INPUT", "Invalid media mode or ASR backend")
        if not language.isalpha() or len(language) > 12:
            raise AgentError("INVALID_INPUT", "Language must be auto or a Whisper language code")
        snapshot = self.store.resource("snapshots", snapshot_id)
        if not snapshot["complete"] and not allow_partial:
            raise AgentError("INCOMPLETE_SOURCE", "Discovery is incomplete; increase its limit or explicitly allow a partial plan")
        select, exclude = set(select or []), set(exclude or [])
        available = {i["bvid"] for i in snapshot["items"]}
        if (select | exclude) - available:
            raise AgentError("INVALID_SELECTION", "Selection contains IDs outside the snapshot")
        items, omitted = [], []
        for item in snapshot["items"]:
            text = (item["title"] + " " + item.get("description", "")).casefold()
            selected = (not select or item["bvid"] in select) and item["bvid"] not in exclude and (not keywords or any(k.casefold() in text for k in keywords))
            (items if selected else omitted).append(item)
        if not items:
            raise AgentError("EMPTY_SELECTION", "No videos match the selected IDs or keywords")
        plan = self.store.save_resource("plans", {"snapshot_id": snapshot_id, "source": snapshot["source"], "source_complete": snapshot["complete"], "items": items, "excluded": [{"bvid": i["bvid"], "title": i["title"], "reason": "explicit selection or keyword filter"} for i in omitted], "options": {"mode": mode, "asr": asr, "language": language, "summarize": bool(summarize)}, "video_count": len(items), "parts_policy": "all", "parts_total": None})
        return plan

    def start(self, plan_id, *, idempotency_key=None, background=True):
        job, created = self.store.create_job(plan_id, idempotency_key)
        if created:
            if background:
                self._spawn(job["id"])
            else:
                self.run(job["id"])
        return self.status(job["id"])

    def _spawn(self, job_id):
        env = os.environ.copy()
        env["BILIDIGEST_DATA_DIR"] = str(self.store.root.parent)
        env["BILIDIGEST_OUTPUT_DIR"] = str(self.store.output.parent)
        root = str(Path(__file__).resolve().parents[2])
        env["PYTHONPATH"] = root + os.pathsep + env.get("PYTHONPATH", "")
        log = self.store.root / (job_id + ".log")
        with log.open("a", encoding="utf-8") as stream:
            subprocess.Popen([sys.executable, "-m", "tools.agent.cli", "_worker", job_id], env=env, stdin=subprocess.DEVNULL, stdout=stream, stderr=stream, start_new_session=True, close_fds=True)

    def resume(self, job_id, *, background=True):
        try:
            with self.store.lock(job_id).acquire(timeout=0):
                self.store.job(job_id)
                self.store.requeue(job_id)
        except Timeout:
            raise AgentError("JOB_BUSY", "A worker already owns this job")
        if background:
            self._spawn(job_id)
        else:
            self.run(job_id)
        return self.status(job_id)

    def status(self, job_id):
        job = self.store.job(job_id)
        parts = list(job.get("parts", {}).values())
        job["counts"] = {"videos_selected": job["video_count"], "parts_discovered": len(parts), "media_verified": sum(bool(p.get("validation")) for p in parts), "transcripts_ready": sum(bool(p.get("transcript")) for p in parts), "summaries_ready": sum(bool(p.get("summary")) for p in parts)}
        job["output_dir"] = str(self.store.job_dir(job_id))
        return job

    def run(self, job_id):
        try:
            with self.store.lock(job_id).acquire(timeout=0):
                # One active collection worker per data directory bounds aggregate API traffic.
                with FileLock(str(self.store.root / "worker.lock")):
                    self._run_locked(job_id)
        except Timeout:
            raise AgentError("JOB_BUSY", "A worker already owns this job")

    def _run_locked(self, job_id):
        job = self.store.job(job_id)
        if job["state"] != "queued":
            return
        plan = self.store.resource("plans", job["plan_id"])
        folder = self.store.job_dir(job_id)
        options = plan["options"]
        cancelled = lambda: self.store.cancelled(job_id)
        job.update(state="running", errors=[], pid=os.getpid(), started_at=time.time())
        self.store.save_job(job)
        try:
            for selected in plan["items"]:
                if cancelled():
                    raise AgentError("CANCELLED", "Job cancelled")
                bv = selected["bvid"]
                meta_path = folder / "metadata" / (bv + ".json")
                try:
                    if meta_path.exists():
                        video = json.loads(meta_path.read_text(encoding="utf-8"))
                    else:
                        video = platform.video_metadata(self.client, bv)
                        atomic_json(meta_path, video)
                    if not video.get("pages"):
                        raise AgentError("NO_PLAYABLE_MEDIA", "No playable parts were returned")
                except (LoginRequired, RiskControl):
                    raise
                except Exception as exc:
                    job["errors"].append({"bvid": bv, "stage": "metadata", **error_payload(exc)})
                    self.store.save_job(job)
                    continue
                for page in video["pages"]:
                    key = f'{bv}_{page["cid"]}'
                    part = job["parts"].setdefault(key, {"bvid": bv, "cid": page["cid"], "page": page["page"], "title": video["title"], "part_title": page.get("part", ""), "source_url": f'https://www.bilibili.com/video/{bv}?p={page["page"]}'})
                    part.pop("error", None)
                    try:
                        if cancelled():
                            raise AgentError("CANCELLED", "Job cancelled")
                        part["stage"] = "media"
                        self.store.save_job(job)
                        audio = folder / part["media"] if part.get("media") else None
                        valid = audio and audio.exists() and part.get("validation", {}).get("sha256") == sha256(audio)
                        if not valid:
                            part.pop("validation", None)
                            audio = media.download_media(self.client, video, page, options["mode"], folder / "media", cancelled)
                            part["media"] = str(audio.relative_to(folder))
                            part["validation"] = media.validate_media(audio, page.get("duration", 0), cancelled)
                        self.store.save_job(job)
                        part["stage"] = "subtitle"
                        text_path = folder / "transcripts" / (key + ".json")
                        valid_text = text_path.is_file() and part.get("transcript_sha256") == sha256(text_path)
                        if not valid_text:
                            transcript = None
                            if part.get("subtitle_state") != "unavailable":
                                transcript = media.existing_subtitle(self.client, video, page)
                                part["subtitle_state"] = "available" if transcript else "unavailable"
                                self.store.save_job(job)
                            if transcript is None and options["asr"] in ("whisper-cpp", "qwen3-asr"):
                                part["stage"] = "asr"
                                self.store.save_job(job)
                                if options["asr"] == "qwen3-asr":
                                    from . import qwen_asr
                                    transcriber, model_path = qwen_asr.transcribe, self.qwen_model()
                                else:
                                    transcriber, model_path = media.transcribe, self.whisper_model()
                                transcript = transcriber(audio, self.store.root / "asr-cache", folder / "work" / key, model=model_path, language=options["language"], cancelled=cancelled)
                            if transcript:
                                media.write_transcript(text_path, transcript, video, page)
                                part.update(transcript=str(text_path.relative_to(folder)), transcript_sha256=sha256(text_path), transcript_source=transcript["source"], asr_cache_hit=transcript.get("cache_hit", False))
                            else:
                                part["text_state"] = "unavailable_asr_disabled"
                        self.store.save_job(job)
                        if options["summarize"]:
                            part["stage"] = "summary"
                            if not part.get("transcript"):
                                raise AgentError("NO_TRANSCRIPT", "Full-text summary requires a transcript; enable ASR or change the plan")
                            summary = folder / part["summary"] if part.get("summary") else None
                            if not summary or not summary.is_file() or part.get("summary_transcript_sha256") != part["transcript_sha256"]:
                                from ..bili_digest import export_transcript_digest
                                result = export_transcript_digest({"paths": {"json": str(text_path)}}, out_dir=folder / "summaries" / key)
                                part["summary"] = str(Path(result["path"]).relative_to(folder))
                                part["summary_transcript_sha256"] = part["transcript_sha256"]
                        part["stage"] = "complete"
                    except (LoginRequired, RiskControl):
                        raise
                    except Exception as exc:
                        if isinstance(exc, AgentError) and exc.code == "CANCELLED":
                            raise
                        part["error"] = {"stage": part["stage"], **error_payload(exc)}
                        job["errors"].append({"bvid": bv, "cid": page["cid"], **part["error"]})
                    self.store.save_job(job)
            if cancelled():
                raise AgentError("CANCELLED", "Job cancelled")
            job["state"] = "partial" if job["errors"] else "complete"
        except Exception as exc:
            error = error_payload(exc)
            job["errors"].append(error)
            job["state"] = "cancelled" if error["code"] == "CANCELLED" else "blocked" if error["code"] in ("AUTH_REQUIRED", "RISK_BLOCKED") else "failed"
        finally:
            job["finished_at"] = time.time()
            self.store.save_job(job)
            try:
                self._export(job)
            except Exception as exc:
                job["errors"].append({"stage": "export", **error_payload(exc)})
                job["state"] = "partial" if job["state"] == "complete" else job["state"]
                self.store.save_job(job)

    def _export(self, job):
        folder = self.store.job_dir(job["id"])
        rows, chunks, combined, seen = [], [], [], set()
        index = ["# BiliDigest collection", "", f'Job: {job["id"]}', f'Status: {job["state"]}', "", "Automatic transcripts may contain recognition errors. No visual analysis is implied.", ""]
        for part in job["parts"].values():
            row = {k: part.get(k, "") for k in ("title", "bvid", "cid", "page", "part_title", "source_url", "media", "transcript", "transcript_source", "summary", "text_state")}
            rows.append(row)
            index += [f'## {part["title"]} · P{part["page"]}', "", f'[Source]({part["source_url"]})']
            for label, field in (("Media", "media"), ("Transcript JSON", "transcript"), ("Summary", "summary")):
                if part.get(field):
                    index.append(f'- [{label}]({quote(part[field])})')
            if part.get("error"):
                index.append(f'- Incomplete: {part["error"]["code"]}')
            if part.get("text_state"):
                index.append("- No transcript; ASR was disabled.")
            text = folder / part["transcript"] if part.get("transcript") else None
            if text and text.exists():
                value = json.loads(text.read_text(encoding="utf-8"))
                part["timestamp_kind"] = value.get("timestamp_kind", "model_segments")
                combined.append(text.with_suffix(".md").read_text(encoding="utf-8"))
                fingerprint = part.get("validation", {}).get("sha256")
                if fingerprint in seen:
                    continue
                seen.add(fingerprint)
                window, start = [], None
                for line in value["body"]:
                    if start is None:
                        start = line["from"]
                    if window and (line["from"] - start >= 180 or sum(len(r["content"]) for r in window) >= 1800):
                        chunks.append(self._chunk(part, window, len(chunks)))
                        window = []
                        start = line["from"]
                    window.append(line)
                if window:
                    chunks.append(self._chunk(part, window, len(chunks)))
        with (folder / "catalog.csv").open("w", encoding="utf-8-sig", newline="") as f:
            if rows:
                writer = csv.DictWriter(f, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)
        (folder / "README.md").write_text("\n".join(index) + "\n", encoding="utf-8")
        (folder / "transcripts.md").write_text("\n\n---\n\n".join(combined), encoding="utf-8")
        (folder / "knowledge.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in chunks), encoding="utf-8")
        atomic_json(folder / "manifest.json", {"schema_version": "1.0", "job_id": job["id"], "state": job["state"], "errors": job["errors"], "parts": job["parts"], "chunks": len(chunks)})
        artifacts = []
        for p in sorted(folder.rglob("*")):
            rel = p.relative_to(folder)
            if p.is_file() and p.resolve().is_relative_to(folder.resolve()) and rel.parts[0] != "work" and not p.name.endswith((".part", ".transfer.json", ".zip", ".tmp")):
                artifacts.append({"path": str(rel), "bytes": p.stat().st_size})
        job["artifacts"] = artifacts
        self.store.save_job(job)
        return {"job_id": job["id"], "state": job["state"], "output_dir": str(folder), "artifacts": artifacts, "chunks": len(chunks)}

    @staticmethod
    def _chunk(part, window, n):
        start = window[0]["from"]
        return {"id": f'{part["bvid"]}_{part["cid"]}_{n:06d}', "title": part["title"], "bvid": part["bvid"], "cid": part["cid"], "page": part["page"], "start_seconds": start, "end_seconds": window[-1]["to"], "source_url": part["source_url"] + f"&t={int(start)}", "transcript_source": part["transcript_source"], "timestamp_kind": part.get("timestamp_kind", "model_segments"), "text": "\n".join(r["content"] for r in window)}

    def export(self, job_id, *, include_media=False):
        try:
            with self.store.lock(job_id).acquire(timeout=0):
                job = self.store.job(job_id)
                result = self._export(job)
                folder = self.store.job_dir(job_id)
                archive = folder / ("collection.zip" if include_media else "documents.zip")
                temp = archive.with_suffix(".zip.tmp")
                with zipfile.ZipFile(temp, "w", compression=zipfile.ZIP_DEFLATED) as z:
                    for item in result["artifacts"]:
                        rel = Path(item["path"])
                        if include_media or rel.parts[0] != "media":
                            z.write(folder / rel, str(rel), compress_type=zipfile.ZIP_STORED if rel.parts[0] == "media" else zipfile.ZIP_DEFLATED)
                temp.replace(archive)
                job["artifacts"].append({"path": archive.name, "bytes": archive.stat().st_size})
                self.store.save_job(job)
                return {**result, "archive": str(archive)}
        except Timeout:
            raise AgentError("JOB_BUSY", "Wait until the worker stops before exporting an archive")

    def artifact(self, job_id, name):
        job = self.store.job(job_id)
        if name not in {a["path"] for a in job["artifacts"]}:
            raise AgentError("NOT_FOUND", "Artifact is not in this job's manifest")
        root = self.store.job_dir(job_id).resolve()
        path = (root / name).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise AgentError("NOT_FOUND", "Artifact not found")
        return path
