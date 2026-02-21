from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
import json
import shutil
from typing import Optional
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# Import existing automation logic
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import Jack_Discord
import Jack_Google
import Jack_Insta

import sys
import io
import threading
from collections import deque

# --- Logging Infrastructure ---
class LogBuffer(io.StringIO):
    def __init__(self, maxlen=500):
        super().__init__()
        self.buffer = deque(maxlen=maxlen)
        self.lock = threading.Lock()

    def write(self, s):
        if s:
            with self.lock:
                # Add timestamp to each log line for the console
                timestamp = datetime.now().strftime("%H:%M:%S")
                # Strip trailing newlines to avoid empty lines in the UI
                clean_s = s.rstrip('\n')
                if clean_s:
                    for line in clean_s.split('\n'):
                        self.buffer.append(f"[{timestamp}] {line}")
        return super().write(s)

    def get_logs(self):
        with self.lock:
            return list(self.buffer)

log_buffer = LogBuffer()
# Intercept stdout and stderr
sys.stdout = log_buffer
sys.stderr = log_buffer

def normalize_timezone(tz_name):
    """Maps common timezone abbreviations to IANA names."""
    if not tz_name:
        return "UTC"
    mapping = {
        "EST": "America/New_York",
        "EDT": "America/New_York",
        "CST": "America/Chicago",
        "CDT": "America/Chicago",
        "MST": "America/Denver",
        "MDT": "America/Denver",
        "PST": "America/Los_Angeles",
        "PDT": "America/Los_Angeles",
    }
    normalized = mapping.get(str(tz_name).upper(), tz_name)
    if normalized != tz_name:
        print(f"[System] Normalizing timezone '{tz_name}' -> '{normalized}'")
    return normalized

# --- App Initialization ---
app = FastAPI()

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust as needed for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVENT_DETAILS_FILE = os.path.join(BASE_DIR, "event_details.json")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
STATIC_DIR = os.path.join(BASE_DIR, "frontend", "dist")

if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

def load_details():
    if os.path.exists(EVENT_DETAILS_FILE) and os.path.getsize(EVENT_DETAILS_FILE) > 0:
        with open(EVENT_DETAILS_FILE, "r") as file:
            details = json.load(file)
            details['timezone'] = normalize_timezone(details.get('timezone', 'UTC'))
            return details
    return {}

def save_details(details):
    with open(EVENT_DETAILS_FILE, "w") as file:
        json.dump(details, file, indent=4)

@app.get("/api/details")
async def get_details():
    return load_details()

@app.post("/api/details")
async def update_details(details: dict):
    save_details(details)
    return {"status": "success", "message": "Details updated"}

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return {"status": "success", "file_path": file_path}

@app.post("/api/actions/{action}")
async def execute_action(action: str):
    details = load_details()
    try:
        if action == "discord":
            await Jack_Discord.run_discord_task(details)
        elif action == "email":
            Jack_Google.send_email_to_list(details)
        elif action == "calendar":
            Jack_Google.add_to_google_calendar(details)
        elif action == "instagram":
            Jack_Insta.instagram_post(details)
        elif action == "custom":
            Jack_Google.send_custom_emails(details, details.get("custom emails list", ""))
        elif action == "all":
            await Jack_Discord.run_discord_task(details)
            Jack_Google.send_email_to_list(details)
            Jack_Google.add_to_google_calendar(details)
            Jack_Insta.instagram_post(details)
            Jack_Google.send_custom_emails(details, details.get("custom emails list", ""))
        else:
            raise HTTPException(status_code=400, detail="Invalid action")
            
        return {"status": "success", "message": f"Action {action} executed"}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/auth/status")
async def google_auth_status():
    """Returns the current authentication status (logged in user email)."""
    return Jack_Google.get_auth_status()

@app.get("/api/logs")
async def get_app_logs():
    """Returns the captured stdout/stderr logs."""
    return {"logs": log_buffer.get_logs()}

@app.get("/api/auth/google")
async def google_auth_init():
    """Returns the Google authorization URL."""
    try:
        auth_url = Jack_Google.get_google_auth_url()
        return {"auth_url": auth_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/auth/callback")
async def google_auth_callback(code: str):
    """Handles the Google OAuth callback and saves the token."""
    try:
        Jack_Google.handle_google_callback(code)
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Serve Frontend static files
if os.path.exists(STATIC_DIR):
    app.mount("/assets", StaticFiles(directory=os.path.join(STATIC_DIR, "assets")), name="assets")
    # Also mount the uploads directory so images can be served if a tunnel is used
    if os.path.exists(UPLOAD_DIR):
        app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        # Serve index.html for all non-API routes to handle SPA routing
        if not full_path.startswith("api"):
            index_path = os.path.join(STATIC_DIR, "index.html")
            if os.path.exists(index_path):
                return FileResponse(index_path)
        raise HTTPException(status_code=404, detail="Not found")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
