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
            return json.load(file)
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
            Jack_Discord.call_post_event(details)
        elif action == "email":
            Jack_Google.send_email_to_list(details)
        elif action == "calendar":
             # Need to handle potential redirect URI issues in hosted environment later
            Jack_Google.add_to_google_calendar(details)
        elif action == "instagram":
            # Modified Jack_Insta.instagram_post to accept details
            Jack_Insta.instagram_post(details)
        elif action == "custom":
            Jack_Google.send_custom_emails(details, details.get("custom emails list", ""))
        elif action == "all":
            # Sequential execution
            Jack_Discord.call_post_event(details)
            Jack_Google.send_email_to_list(details)
            Jack_Google.add_to_google_calendar(details)
            Jack_Insta.instagram_post(details)
            Jack_Google.send_custom_emails(details, details.get("custom emails list", ""))
        else:
            raise HTTPException(status_code=400, detail="Invalid action")
            
        return {"status": "success", "message": f"Action {action} executed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
        return {"status": "success", "message": "Authentication successful! You can close this tab."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Serve Frontend static files
if os.path.exists(STATIC_DIR):
    app.mount("/assets", StaticFiles(directory=os.path.join(STATIC_DIR, "assets")), name="assets")

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
