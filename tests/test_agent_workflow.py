import json
import subprocess
import sys
from pathlib import Path

import pytest

from tools.agent import media, platform
from tools.agent.service import Service
from tools.agent.store import AgentError, Store, sha256
from tools.bili_client import RiskControl


BV = "BV1234567890"


class FakeClient:
    cookies = {}


@pytest.fixture
def service(tmp_path):
    return Service(Store(tmp_path / "data", tmp_path / "output"), FakeClient())


def make_plan(service, **options):
    snapshot = service.store.save_resource("snapshots", {"source": BV, "complete": True, "items": [{"bvid": BV, "title": "example"}]})
    return service.plan(snapshot["id"], **options)


def fake_pipeline(monkeypatch, service, pages=2):
    calls = {"download": [], "asr": []}
    video = {"bvid": BV, "aid": 123, "title": "example", "pages": [{"cid": 10 + n, "page": n + 1, "part": f"part{n}", "duration": 5} for n in range(pages)]}
    monkeypatch.setattr(platform, "video_metadata", lambda client, bv: video)

    def download(client, video, page, mode, folder, cancelled):
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f'{page["cid"]}.m4a'
        path.write_bytes(f'example-audio-{page["cid"]}'.encode())
        calls["download"].append(page["cid"])
        return path

    monkeypatch.setattr(media, "download_media", download)
    monkeypatch.setattr(media, "validate_media", lambda path, duration, cancelled: {"sha256": sha256(path), "seconds": 5, "bytes": path.stat().st_size, "full_decode": True})
    monkeypatch.setattr(media, "existing_subtitle", lambda client, video, page: {"source": "bilibili_subtitle", "body": [{"from": 0, "to": 5, "content": f'part {page["page"]}'}]})
    return calls


def test_all_parts_artifacts_and_idempotence(service, monkeypatch):
    calls = fake_pipeline(monkeypatch, service)
    plan = make_plan(service)
    result = service.start(plan["id"], idempotency_key="once", background=False)
    assert result["state"] == "complete"
    assert result["counts"]["media_verified"] == 2
    assert result["counts"]["transcripts_ready"] == 2
    assert calls["download"] == [10, 11]
    again = service.start(plan["id"], idempotency_key="once", background=False)
    assert again["id"] == result["id"]
    service.resume(result["id"], background=False)
    assert calls["download"] == [10, 11]
    output = service.export(result["id"])
    import zipfile
    with zipfile.ZipFile(output["archive"]) as z:
        assert "knowledge.jsonl" in z.namelist()
        assert not any(n.startswith("media/") for n in z.namelist())
    with pytest.raises(AgentError, match="different plan"):
        service.start(make_plan(service)["id"], idempotency_key="once", background=False)


def test_resume_missing_asr_does_not_redownload(service, monkeypatch):
    calls = fake_pipeline(monkeypatch, service, pages=1)
    monkeypatch.setattr(media, "existing_subtitle", lambda *a: None)
    monkeypatch.setattr(media, "transcribe", lambda *a, **kw: (_ for _ in ()).throw(AgentError("ASR_UNAVAILABLE", "missing model")))
    plan = make_plan(service, asr="whisper-cpp")
    job = service.start(plan["id"], background=False)
    assert job["state"] == "partial"
    assert job["counts"]["media_verified"] == 1
    monkeypatch.setattr(media, "transcribe", lambda *a, **kw: {"source": "whisper.cpp", "body": [{"from": 0, "to": 5, "content": "recovered"}]})
    resumed = service.resume(job["id"], background=False)
    assert resumed["state"] == "complete"
    assert calls["download"] == [10]
    assert resumed["counts"]["transcripts_ready"] == 1


def test_cancel_column_cannot_be_lost_by_stale_worker(service):
    job, _ = service.store.create_job(make_plan(service)["id"])
    stale = dict(job)
    service.store.cancel(job["id"])
    service.store.save_job(stale, "running")
    assert service.store.cancelled(job["id"])


def test_running_lock_prevents_duplicate_resume(service):
    job, _ = service.store.create_job(make_plan(service)["id"])
    with service.store.lock(job["id"]):
        with pytest.raises(AgentError, match="worker"):
            service.resume(job["id"], background=False)


def test_risk_control_stops_without_requesting_other_parts(service, monkeypatch):
    calls = fake_pipeline(monkeypatch, service)
    monkeypatch.setattr(media, "existing_subtitle", lambda *args: (_ for _ in ()).throw(RiskControl()))
    job = service.start(make_plan(service)["id"], background=False)
    assert job["state"] == "blocked"
    assert calls["download"] == [10]
    assert job["errors"][0]["code"] == "RISK_BLOCKED"


def test_corrupted_completed_media_is_not_skipped(service, monkeypatch):
    calls = fake_pipeline(monkeypatch, service, 1)
    job = service.start(make_plan(service)["id"], background=False)
    part = next(iter(job["parts"].values()))
    (service.store.job_dir(job["id"]) / part["media"]).write_bytes(b"corrupt")
    result = service.resume(job["id"], background=False)
    assert calls["download"] == [10, 10]
    assert result["state"] == "complete"


def test_incomplete_discovery_requires_explicit_partial_plan(service):
    s = service.store.save_resource("snapshots", {"source": "mid:1", "complete": False, "items": [{"bvid": BV, "title": "sample"}]})
    with pytest.raises(AgentError) as e:
        service.plan(s["id"])
    assert e.value.code == "INCOMPLETE_SOURCE"
    assert service.plan(s["id"], allow_partial=True)["video_count"] == 1


def test_pagination_and_nonprogress_detection():
    class Client:
        def __init__(self): self.pages = []
        def request_json(self, url, params, **kwargs):
            self.pages.append(params["pn"])
            rows = [{"bvid": f"BV{n:010d}", "title": str(n), "length": "01:00"} for n in range(50)] if params["pn"] == 1 else [{"bvid": "BV9999999999", "title": "last", "length": "01:00"}]
            return {"data": {"page": {"count": 51}, "list": {"vlist": rows}}}
    c = Client()
    result = platform.discover(c, "mid:1")
    assert c.pages == [1, 2]
    assert result["complete"] and result["fetched_count"] == 51
    short = platform.discover(Client(), "mid:1", 1)
    assert not short["complete"]


@pytest.mark.parametrize("url", ["http://127.0.0.1/x", "https://localhost/x", "https://bilibili.com.evil.test/video/x", "https://user:password@www.bilibili.com/video/x", "https://www.bilibili.com:8443/video/x", "file:///etc/passwd"])
def test_discovery_rejects_untrusted_urls(url):
    with pytest.raises(AgentError):
        platform.resource_ref(url)


def test_stream_resume_uses_matching_range(tmp_path, monkeypatch):
    path = tmp_path / "test.m4a"
    path.with_suffix(".m4a.part").write_bytes(b"abc")
    seen = []
    class Response:
        status_code = 206
        headers = {"Content-Range": "bytes 3-5/6", "Content-Length": "3"}
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def raise_for_status(self): pass
        def iter_content(self, n): yield b"def"
    def get(url, headers=None):
        seen.append(headers)
        return Response()
    monkeypatch.setattr(media, "public_get", get)
    media.download_file(["https://cdn.bilivideo.com/x"], path)
    assert seen[0]["Range"] == "bytes=3-"
    assert path.read_bytes() == b"abcdef"


def test_cli_machine_readable_argument_error(tmp_path):
    run = subprocess.run([sys.executable, "-m", "tools.agent.cli", "--data-dir", str(tmp_path), "plan"], capture_output=True, text=True)
    assert run.returncode == 1
    payload = json.loads(run.stdout)
    assert payload["error"]["code"] == "INVALID_ARGUMENT"
