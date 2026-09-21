"""FastAPI application: HTTP routes only.

All real work lives in the ``sawed_off`` package; this file wires it to URLs.

Route map
---------
GET  /api/health                 liveness check (for Docker / uptime monitors)
GET  /api/auth/session           is a password required? am I logged in?
POST /api/auth/login             {"password": ...} -> sets session cookie
POST /api/auth/logout
GET  /api/details                saved event details
POST /api/details                save event details (validated)
POST /api/upload                 multipart file -> stored under DATA_DIR/uploads
GET  /api/custom-emails          names of the custom email templates
POST /api/actions/{action}       start a background job -> {job}
GET  /api/actions/{action}/check preflight problems without running anything
GET  /api/jobs                   recent jobs
GET  /api/jobs/{id}              one job (status, error, log lines)
GET  /api/logs                   global debug log ring buffer
GET  /api/google/status          Google login status
GET  /api/google/login           -> {"auth_url"}  (browser navigates there)
GET  /api/auth/callback          Google redirects here after consent
POST /api/google/logout
"""

from __future__ import annotations

import logging
import re
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ValidationError

from sawed_off import __version__, actions, auth, config, jobs, storage
from sawed_off.integrations import google_apis
from sawed_off.logbuffer import ring_handler, setup_logging
from sawed_off.models import ACTIONS, EventDetails

log = logging.getLogger("sawed_off.web")

MAX_UPLOAD_BYTES = 25 * 1024 * 1024
ALLOWED_UPLOAD_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".csv", ".txt"}


@asynccontextmanager
async def lifespan(_: FastAPI):
    setup_logging()
    config.ensure_data_dirs()
    for moved in config.migrate_legacy_files():
        log.info("Migrated legacy file: %s", moved)
    log.info("Sawed-off-Socials v%s ready. Data directory: %s", __version__, config.DATA_DIR)
    if not auth.auth_required():
        log.warning("APP_PASSWORD is not set: anyone who can reach this server can use it.")
    yield


app = FastAPI(title="Sawed-off-Socials", version=__version__, lifespan=lifespan)
app.add_middleware(auth.AuthMiddleware)


# --- Health & auth ---------------------------------------------------------------

@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok", "version": __version__}


class LoginBody(BaseModel):
    password: str = ""


@app.get("/api/auth/session")
async def session(request: Request) -> dict:
    return {
        "auth_required": auth.auth_required(),
        "authenticated": auth.is_authenticated(request),
        "version": __version__,
    }


@app.post("/api/auth/login")
async def login(body: LoginBody, request: Request) -> JSONResponse:
    client_ip = request.client.host if request.client else "unknown"
    if auth.too_many_failures(client_ip):
        raise HTTPException(status_code=429, detail="Too many attempts. Try again in a minute.")
    if not auth.check_password(body.password):
        auth.record_failure(client_ip)
        raise HTTPException(status_code=401, detail="Wrong password")
    response = JSONResponse({"status": "ok"})
    response.set_cookie(
        auth.COOKIE_NAME,
        auth.session_token(),
        max_age=auth.COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=request.url.scheme == "https",
        path="/",
    )
    return response


@app.post("/api/auth/logout")
async def logout() -> JSONResponse:
    response = JSONResponse({"status": "ok"})
    response.delete_cookie(auth.COOKIE_NAME, path="/")
    return response


# --- Event details ------------------------------------------------------------------

@app.get("/api/details")
async def get_details() -> dict:
    return storage.load_details().model_dump()


@app.post("/api/details")
async def update_details(raw: dict) -> dict:
    try:
        details = EventDetails.from_raw(raw)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=_format_validation_error(exc)) from exc
    storage.save_details(details)
    return {"status": "ok", "details": details.model_dump()}


def _format_validation_error(exc: ValidationError) -> str:
    parts = []
    for err in exc.errors():
        field = ".".join(str(p) for p in err.get("loc", ())) or "details"
        msg = err.get("msg", "invalid")
        msg = re.sub(r"^Value error, ", "", msg)
        parts.append(f"{field}: {msg}")
    return "; ".join(parts)


# --- Uploads -------------------------------------------------------------------

def safe_filename(name: str) -> str:
    """Strip directories and odd characters so uploads cannot escape UPLOAD_DIR."""
    base = Path(name or "upload").name
    base = re.sub(r"[^A-Za-z0-9._ -]+", "_", base).strip(" .")
    return base or "upload"


@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)) -> dict:
    name = safe_filename(file.filename or "")
    suffix = Path(name).suffix.lower()
    if suffix not in ALLOWED_UPLOAD_SUFFIXES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{suffix or '(none)'}'. Allowed: {', '.join(sorted(ALLOWED_UPLOAD_SUFFIXES))}",
        )
    config.ensure_data_dirs()
    target = config.UPLOAD_DIR / name
    if target.exists():
        target = config.UPLOAD_DIR / f"{Path(name).stem}-{uuid.uuid4().hex[:6]}{suffix}"

    size = 0
    with target.open("wb") as out:
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > MAX_UPLOAD_BYTES:
                out.close()
                target.unlink(missing_ok=True)
                raise HTTPException(status_code=413, detail="File larger than 25 MB")
            out.write(chunk)
    log.info("Uploaded %s (%d bytes)", target.name, size)
    return {"status": "ok", "file_path": str(target), "filename": target.name, "url": f"/uploads/{target.name}"}


@app.get("/api/custom-emails")
async def custom_emails() -> dict:
    try:
        templates = storage.load_custom_emails()
    except ValueError as exc:
        return {"names": [], "error": str(exc), "path": str(config.CUSTOM_EMAILS_FILE)}
    return {
        "names": list(templates),
        "path": str(config.CUSTOM_EMAILS_FILE),
        "templates": {k: {"email": v["email"], "subject": v["subject"]} for k, v in templates.items()},
    }


# --- Actions & jobs ----------------------------------------------------------------

def _require_action(action: str) -> None:
    if action not in ACTIONS:
        raise HTTPException(status_code=404, detail=f"Unknown action '{action}'. Valid: {', '.join(ACTIONS)}")


@app.get("/api/actions/{action}/check")
async def check_action(action: str) -> dict:
    _require_action(action)
    problems = actions.preflight(action, storage.load_details())
    return {"action": action, "ok": not problems, "problems": problems}


@app.post("/api/actions/{action}", status_code=202)
async def start_action(action: str) -> dict:
    _require_action(action)
    details = storage.load_details()
    problems = actions.preflight(action, details)
    if problems:
        raise HTTPException(status_code=400, detail={"message": "Cannot run yet", "problems": problems})
    try:
        job = jobs.manager.start(action, lambda: actions.run_action(action, details))
    except jobs.JobAlreadyRunning as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"job": job.to_dict()}


@app.get("/api/jobs")
async def list_jobs() -> dict:
    return {"jobs": [j.to_dict() | {"log": []} for j in jobs.manager.list()]}


@app.get("/api/jobs/{job_id}")
async def get_job(job_id: str) -> dict:
    job = jobs.manager.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="No such job")
    return {"job": job.to_dict()}


@app.get("/api/logs")
async def get_logs() -> dict:
    return {"logs": ring_handler.get_lines()}


# --- Google OAuth -------------------------------------------------------------

@app.get("/api/google/status")
async def google_status() -> dict:
    return google_apis.auth_status()


@app.get("/api/google/login")
async def google_login() -> dict:
    try:
        return {"auth_url": google_apis.authorization_url()}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/auth/callback")
async def google_callback(code: str | None = None, state: str | None = None, error: str | None = None):
    if error or not code:
        log.warning("[Google] Login cancelled or failed: %s", error or "no code")
        return RedirectResponse(url=f"/?google=error&reason={error or 'no_code'}")
    try:
        email = google_apis.handle_callback(code, state)
    except Exception as exc:  # noqa: BLE001
        log.error("[Google] Login failed: %s", exc)
        return RedirectResponse(url="/?google=error&reason=exchange_failed")
    return RedirectResponse(url=f"/?google=ok&email={email}")


@app.post("/api/google/logout")
async def google_logout() -> dict:
    google_apis.logout()
    return {"status": "ok"}


# --- Static frontend ------------------------------------------------------------

config.ensure_data_dirs()
app.mount("/uploads", StaticFiles(directory=str(config.UPLOAD_DIR)), name="uploads")

if config.FRONTEND_DIST.is_dir():
    assets_dir = config.FRONTEND_DIST / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_frontend(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found")
        candidate = (config.FRONTEND_DIST / full_path).resolve()
        if full_path and candidate.is_file() and config.FRONTEND_DIST.resolve() in candidate.parents:
            return FileResponse(candidate)
        return FileResponse(config.FRONTEND_DIST / "index.html")
else:

    @app.get("/", include_in_schema=False)
    async def no_frontend() -> dict:
        return {
            "detail": "Frontend not built. Run `npm install && npm run build` in frontend/, "
                      "or use the Docker image.",
            "api_docs": "/docs",
        }
