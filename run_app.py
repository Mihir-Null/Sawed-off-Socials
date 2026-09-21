"""Local launcher: start the server and open the UI in a browser.

    python run_app.py            # http://localhost:8000
    SOS_PORT=9000 python run_app.py

For servers use uvicorn or Docker directly (see README).
"""

from __future__ import annotations

import os
import threading
import time
import webbrowser

import uvicorn

from sawed_off.config import env

HOST = env("SOS_HOST", "127.0.0.1")
PORT = int(env("SOS_PORT", "8000"))


def open_browser() -> None:
    time.sleep(1.5)
    url = f"http://{'localhost' if HOST in ('0.0.0.0', '127.0.0.1') else HOST}:{PORT}"
    print(f"[Launcher] Opening {url}")
    webbrowser.open(url)


if __name__ == "__main__":
    if not os.environ.get("SOS_NO_BROWSER"):
        threading.Thread(target=open_browser, daemon=True).start()
    uvicorn.run("backend.main:app", host=HOST, port=PORT, log_level="info", proxy_headers=True)
