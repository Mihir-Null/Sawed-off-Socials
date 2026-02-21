import os
import sys
import threading
import webbrowser
import uvicorn
import time
from backend.main import app

def open_browser():
    """Wait for the server to start, then open the browser."""
    # Short delay to ensure server is listening
    time.sleep(1.5)
    print("[Launcher] Opening default web browser to http://localhost:8000...")
    webbrowser.open("http://localhost:8000")

def run_server():
    """Run the FastAPI server."""
    print("[Launcher] Starting backend server on http://0.0.0.0:8000...")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")

if __name__ == "__main__":
    # Start the browser-opening logic in a separate thread
    browser_thread = threading.Thread(target=open_browser)
    browser_thread.daemon = True
    browser_thread.start()

    # Start the server (this blocks until the server is shut down)
    try:
        run_server()
    except KeyboardInterrupt:
        print("\n[Launcher] Shutting down...")
        sys.exit(0)
