import os
import sys
import uuid
import json
import asyncio
import shutil
import logging
import re

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, field_validator
from typing import Optional

# Fix import path so Jack_* modules (in project root) are importable
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import Jack_Discord
import Jack_Google
import Jack_Insta
from utils import (
    log_handler,
    load_event_details,
    save_event_details,
    EVENT_DETAILS_FILE,
    BASE_DIR,
)

logger = logging.getLogger("sawed-off.api")

# --- Pydantic Validation Model ---

class EventDetails(BaseModel):
    event_name: str = Field(default="", max_length=200)
    description: str = Field(default="", max_length=5000)
    image: str = Field(default="")
    server_name: str = Field(default="", max_length=100)
    channel_name: str = Field(default="", max_length=100)
    meeting_link: str = Field(default="", max_length=500)
    event_date: str = Field(default="")
    event_time: str = Field(default="")
    timezone: str = Field(default="America/New_York")
    calendar_name: str = Field(default="", max_length=200)
    csv_file: str = Field(default="")
    email_column: str = Field(default="Email", max_length=100)
    event_duration: int = Field(default=1, ge=1, le=24)
    club_name: str = Field(default="", max_length=200)
    custom_emails_list: str = Field(default="", alias="custom emails list")
    more_info_link: str = Field(default="", max_length=500)

    model_config = {"populate_by_name": True}

    @field_validator("event_date")
    @classmethod
    def validate_date(cls, v):
        if v and not re.match(r"^\d{4}-\d{2}-\d{2}$", v):
            raise ValueError("Date must be YYYY-MM-DD format")
        return v

    @field_validator("event_time")
    @classmethod
    def validate_time(cls, v):
        if v and not re.match(r"^\d{2}:\d{2}$", v):
            raise ValueError("Time must be HH:MM format")
        return v


# --- App Initialization ---

app = FastAPI()

CORS_ORIGINS = os.environ.get(
    "CORS_ORIGINS", "http://localhost:8000,http://localhost:5173"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in CORS_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Paths ---

UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
STATIC_DIR = os.path.join(BASE_DIR, "frontend", "dist")

os.makedirs(UPLOAD_DIR, exist_ok=True)

# --- Upload Security ---

ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".csv"}
MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB


# --- API Endpoints ---

@app.get("/api/details")
async def get_details():
    return load_event_details()


@app.post("/api/details")
async def update_details(details: EventDetails):
    save_event_details(details.model_dump(by_alias=True))
    return {"status": "success", "message": "Details updated"}


@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    safe_name = os.path.basename(file.filename or "upload")
    _, ext = os.path.splitext(safe_name)

    if ext.lower() not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type '{ext}' not allowed. Accepted: {sorted(ALLOWED_EXTENSIONS)}",
        )

    unique_name = f"{uuid.uuid4().hex}_{safe_name}"
    file_path = os.path.join(UPLOAD_DIR, unique_name)

    size = 0
    with open(file_path, "wb") as buffer:
        while chunk := await file.read(8192):
            size += len(chunk)
            if size > MAX_UPLOAD_SIZE:
                os.remove(file_path)
                raise HTTPException(status_code=413, detail="File too large (max 10 MB)")
            buffer.write(chunk)

    return {"status": "success", "file_path": file_path}


@app.post("/api/actions/{action}")
async def execute_action(action: str):
    details = load_event_details()
    try:
        if action == "discord":
            await Jack_Discord.run_discord_task(details)
        elif action == "email":
            await asyncio.to_thread(Jack_Google.send_email_to_list, details)
        elif action == "calendar":
            await asyncio.to_thread(Jack_Google.add_to_google_calendar, details)
        elif action == "instagram":
            await Jack_Insta.instagram_post(details)
        elif action == "custom":
            await asyncio.to_thread(
                Jack_Google.send_custom_emails,
                details,
                details.get("custom emails list", ""),
            )
        elif action == "all":
            results = await asyncio.gather(
                Jack_Discord.run_discord_task(details),
                asyncio.to_thread(Jack_Google.send_email_to_list, details),
                asyncio.to_thread(Jack_Google.add_to_google_calendar, details),
                Jack_Insta.instagram_post(details),
                asyncio.to_thread(
                    Jack_Google.send_custom_emails,
                    details,
                    details.get("custom emails list", ""),
                ),
                return_exceptions=True,
            )

            errors = []
            action_names = ["discord", "email", "calendar", "instagram", "custom_emails"]
            for name, result in zip(action_names, results):
                if isinstance(result, Exception):
                    logger.error("[%s] Failed: %s", name, result)
                    errors.append(f"{name}: {result}")

            if errors:
                raise HTTPException(
                    status_code=207,
                    detail={"partial_failures": errors, "message": "Some actions failed"},
                )

            return {"status": "success", "message": "All actions executed"}
        else:
            raise HTTPException(status_code=400, detail="Invalid action")

        return {"status": "success", "message": f"Action {action} executed"}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("[Action] %s failed", action)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/auth/status")
async def google_auth_status():
    return Jack_Google.get_auth_status()


@app.get("/api/logs")
async def get_app_logs():
    return {"logs": log_handler.get_logs()}


@app.get("/api/auth/google")
async def google_auth_init():
    try:
        auth_url = Jack_Google.get_google_auth_url()
        return {"auth_url": auth_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/auth/callback")
async def google_auth_callback(code: str):
    try:
        Jack_Google.handle_google_callback(code)
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Serve Frontend ---

if os.path.exists(STATIC_DIR):
    app.mount("/assets", StaticFiles(directory=os.path.join(STATIC_DIR, "assets")), name="assets")
    if os.path.exists(UPLOAD_DIR):
        app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        if not full_path.startswith("api"):
            index_path = os.path.join(STATIC_DIR, "index.html")
            if os.path.exists(index_path):
                return FileResponse(index_path)
        raise HTTPException(status_code=404, detail="Not found")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
