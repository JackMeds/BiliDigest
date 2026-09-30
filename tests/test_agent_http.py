import pytest
from fastapi.testclient import TestClient

from tools.agent.http import create_app
from tools.agent.service import Service
from tools.agent.store import Store


TOKEN = "test-only-token-" + "x" * 32


@pytest.fixture
def setup(tmp_path):
    store = Store(tmp_path / "data", tmp_path / "out")
    return store, TestClient(create_app(store, TOKEN))


def test_http_requires_token_including_schema(setup):
    store, client = setup
    assert client.get("/health").status_code == 200
    assert client.get("/v1/jobs").status_code == 401
    assert client.get("/openapi.json").status_code == 401
    result = client.get("/openapi.json", headers={"Authorization": f"Bearer {TOKEN}"})
    assert result.status_code == 200
    assert "/v1/jobs/{job_id}/artifact" in result.json()["paths"]
    assert result.json()["components"]["securitySchemes"]["HTTPBearer"]["scheme"] == "bearer"


def test_http_uses_shared_plan_and_state(setup):
    store, client = setup
    headers = {"Authorization": f"Bearer {TOKEN}"}
    snap = store.save_resource("snapshots", {"source": "mid:1", "complete": True, "items": [{"bvid": "BV1234567890", "title": "sample"}]})
    plan = client.post("/v1/plans", headers=headers, json={"snapshot_id": snap["id"]}).json()["data"]
    job, _ = store.create_job(plan["id"])
    result = client.get(f'/v1/jobs/{job["id"]}', headers=headers)
    assert result.json()["data"]["state"] == "queued"
    response = client.post(f'/v1/jobs/{job["id"]}/cancel', headers=headers)
    assert response.json()["data"]["cancel_requested"]
    assert response.json()["data"]["state"] == "cancelled"


def test_artifact_download_is_manifest_scoped(setup):
    store, client = setup
    headers = {"Authorization": f"Bearer {TOKEN}"}
    snap = store.save_resource("snapshots", {"source": "mid:1", "complete": True, "items": [{"bvid": "BV1234567890", "title": "sample"}]})
    service = Service(store)
    plan = service.plan(snap["id"])
    job, _ = store.create_job(plan["id"])
    output = store.job_dir(job["id"])
    (output / "README.md").write_text("hello")
    job["artifacts"] = [{"path": "README.md"}]
    store.save_job(job)
    url = f'/v1/jobs/{job["id"]}/artifact'
    assert client.get(url, params={"path": "README.md"}, headers=headers).text == "hello"
    assert client.get(url, params={"path": "../../session.json"}, headers=headers).status_code == 404
    secret = store.root / "private.txt"
    secret.write_text("should not be exposed")
    (output / "README.md").unlink()
    (output / "README.md").symlink_to(secret)
    assert client.get(url, params={"path": "README.md"}, headers=headers).status_code == 404


def test_api_does_not_accept_arbitrary_local_paths(setup):
    _, client = setup
    r = client.post("/v1/discover", headers={"Authorization": f"Bearer {TOKEN}"}, json={"source": "file:///etc/passwd"})
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "INVALID_URL"
    assert client.post("/v1/plans", headers={"Authorization": f"Bearer {TOKEN}"}, json={"snapshot_id": "x", "output_dir": "/tmp"}).status_code == 422
