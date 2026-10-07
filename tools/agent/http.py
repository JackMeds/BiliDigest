"""Optional authenticated HTTP transport; deliberately independent of MCP."""
import hmac
import os
import secrets
import sys
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.exceptions import RequestValidationError
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from . import VERSION
from .service import Service, error_payload
from .store import AgentError, Store
from ..bili_client import BiliError


class Body(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DiscoverBody(Body):
    source: str = Field(max_length=2048)
    limit: int = Field(default=1000, ge=1, le=10000)


class PlanBody(Body):
    snapshot_id: str
    select: list[str] | None = None
    exclude: list[str] | None = None
    keywords: list[str] | None = None
    mode: str = "audio-preferred"
    asr: str | None = None
    language: str = "auto"
    summarize: bool = False
    allow_partial: bool = False


class StartBody(Body):
    plan_id: str
    idempotency_key: str | None = Field(default=None, max_length=200)


class ExportBody(Body):
    include_media: bool = False


def create_app(store=None, token=None, service_factory=Service):
    store = store or Store()
    token = token or os.getenv("BILIDIGEST_API_TOKEN")
    if not token or len(token) < 32:
        raise AgentError("TOKEN_REQUIRED", "Set an API token of at least 32 characters")

    bearer = HTTPBearer(auto_error=False)

    def authenticate(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)):
        supplied = credentials.credentials if credentials else ""
        if not credentials or credentials.scheme.lower() != "bearer" or not hmac.compare_digest(supplied.encode(), token.encode()):
            raise HTTPException(401, "A valid Bearer token is required", headers={"WWW-Authenticate": "Bearer"})

    def service():
        # Each request reloads the session, so QR/import changes are immediately visible.
        return service_factory(store)

    app = FastAPI(title="BiliDigest Agent API", version=VERSION, docs_url=None, redoc_url=None, openapi_url=None)
    auth = [Depends(authenticate)]

    @app.exception_handler(HTTPException)
    async def http_error(request, exc):
        return JSONResponse({"ok": False, "error": {"code": "AUTH_INVALID" if exc.status_code == 401 else "HTTP_ERROR", "message": str(exc.detail), "retryable": False}}, status_code=exc.status_code, headers=exc.headers)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        return JSONResponse({"ok": False, "error": {"code": "INVALID_INPUT", "message": "Request does not match the OpenAPI schema", "retryable": False}}, status_code=422)

    @app.exception_handler(BiliError)
    async def platform_error(request, exc):
        return JSONResponse({"ok": False, "error": error_payload(exc)}, status_code=424)

    @app.exception_handler(AgentError)
    async def agent_error(request, exc):
        status = 404 if exc.code == "NOT_FOUND" else 409 if exc.code in ("JOB_BUSY", "IDEMPOTENCY_CONFLICT") else 400
        return JSONResponse({"ok": False, "error": exc.payload()}, status_code=status)

    @app.exception_handler(Exception)
    async def operation_error(request, exc):
        return JSONResponse({"ok": False, "error": error_payload(exc)}, status_code=502)

    def ok(value):
        return {"ok": True, "data": value}

    @app.get("/health", operation_id="health")
    def health():
        return {"ok": True, "version": VERSION}

    @app.get("/openapi.json", dependencies=auth, operation_id="get_api_schema")
    def schema():
        return app.openapi()

    @app.get("/v1/doctor", dependencies=auth, operation_id="doctor")
    def doctor():
        return ok(service().doctor())

    @app.get("/v1/auth", dependencies=auth, operation_id="auth_status")
    def auth_status():
        return ok(service().auth())

    @app.post("/v1/auth/login", dependencies=auth, operation_id="auth_login")
    def login():
        return ok(service().auth("login"))

    @app.get("/v1/auth/poll", dependencies=auth, operation_id="auth_poll")
    def poll(key: str = Query(min_length=1, max_length=200)):
        return ok(service().auth("poll", key))

    @app.post("/v1/discover", dependencies=auth, operation_id="discover")
    def discover(body: DiscoverBody):
        return ok(service().discover(**body.model_dump()))

    @app.get("/v1/snapshots/{snapshot_id}", dependencies=auth, operation_id="read_snapshot")
    def snapshot(snapshot_id: str, offset: int = 0, limit: int = 100):
        return ok(service().snapshot(snapshot_id, offset, limit))

    @app.post("/v1/plans", dependencies=auth, operation_id="create_plan")
    def plan(body: PlanBody):
        return ok(service().plan(**body.model_dump()))

    @app.post("/v1/jobs", dependencies=auth, operation_id="start_job")
    def start(body: StartBody):
        return ok(service().start(**body.model_dump()))

    @app.get("/v1/jobs", dependencies=auth, operation_id="list_jobs")
    def jobs():
        return ok(store.jobs())

    @app.get("/v1/jobs/{job_id}", dependencies=auth, operation_id="job_status")
    def status(job_id: str):
        return ok(service().status(job_id))

    @app.post("/v1/jobs/{job_id}/cancel", dependencies=auth, operation_id="cancel_job")
    def cancel(job_id: str):
        return ok(store.cancel(job_id))

    @app.post("/v1/jobs/{job_id}/resume", dependencies=auth, operation_id="resume_job")
    def resume(job_id: str):
        return ok(service().resume(job_id))

    @app.post("/v1/jobs/{job_id}/export", dependencies=auth, operation_id="export_job")
    def export(job_id: str, body: ExportBody):
        return ok(service().export(job_id, **body.model_dump()))

    @app.get("/v1/jobs/{job_id}/artifact", dependencies=auth, operation_id="download_artifact")
    def artifact(job_id: str, path: str):
        file = service().artifact(job_id, path)
        return FileResponse(file, filename=file.name)

    return app


def serve(store, host="127.0.0.1", port=8765, token_file=None, allow_remote=False):
    if host not in ("127.0.0.1", "localhost", "::1") and not allow_remote:
        raise AgentError("REMOTE_BIND_DISABLED", "Use --allow-remote explicitly and deploy behind HTTPS")
    token_path = Path(token_file) if token_file else store.root / "http.token"
    token = os.getenv("BILIDIGEST_API_TOKEN")
    if not token:
        if not token_path.exists():
            token_path.parent.mkdir(parents=True, exist_ok=True)
            fd = os.open(token_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "w") as f:
                f.write(secrets.token_urlsafe(32))
        token = token_path.read_text().strip()
        print(f"Bearer token file: {token_path} (token is never printed)", file=sys.stderr)
    import uvicorn
    uvicorn.run(create_app(store, token), host=host, port=port, access_log=False)
