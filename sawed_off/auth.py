"""Optional shared-password login for the web UI.

If ``APP_PASSWORD`` is set, every ``/api/*`` and ``/uploads/*`` request must
carry a valid session cookie, obtained by ``POST /api/auth/login``.  The
cookie value is an HMAC of a server secret, so it cannot be forged; it is
``HttpOnly`` so page scripts cannot read it, and ``SameSite=Lax`` so other
sites cannot make requests with it.

If ``APP_PASSWORD`` is *not* set the app is open (the UI shows a warning).
That is fine on a laptop; on a public server, set the password.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import threading
import time

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from .config import app_password, env

COOKIE_NAME = "sos_session"
COOKIE_MAX_AGE = 60 * 60 * 24 * 30  # 30 days

# Paths that never need a login.
PUBLIC_PATHS = {"/api/health", "/api/auth/session", "/api/auth/login"}
PROTECTED_PREFIXES = ("/api/", "/uploads/")

# Random per process unless SOS_SECRET_KEY is set, so sessions survive restarts
# only when the operator opts in.
_SECRET = (env("SOS_SECRET_KEY") or secrets.token_hex(32)).encode()

_fail_lock = threading.Lock()
_failures: dict[str, list[float]] = {}
MAX_FAILURES_PER_MINUTE = 10


def auth_required() -> bool:
    return app_password() is not None


def session_token() -> str:
    """The one valid cookie value for the current password + secret."""
    password = app_password() or ""
    return hmac.new(_SECRET, f"session:v1:{password}".encode(), hashlib.sha256).hexdigest()


def check_password(candidate: str) -> bool:
    expected = app_password()
    if expected is None:
        return True
    return hmac.compare_digest(candidate.encode(), expected.encode())


def is_authenticated(request: Request) -> bool:
    if not auth_required():
        return True
    cookie = request.cookies.get(COOKIE_NAME, "")
    return hmac.compare_digest(cookie, session_token())


def too_many_failures(client_ip: str) -> bool:
    now = time.time()
    with _fail_lock:
        recent = [t for t in _failures.get(client_ip, []) if now - t < 60]
        _failures[client_ip] = recent
        return len(recent) >= MAX_FAILURES_PER_MINUTE


def record_failure(client_ip: str) -> None:
    with _fail_lock:
        _failures.setdefault(client_ip, []).append(time.time())


class AuthMiddleware:
    """Pure ASGI middleware (avoids BaseHTTPMiddleware's streaming quirks)."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not auth_required():
            await self.app(scope, receive, send)
            return
        path = scope.get("path", "")
        if path in PUBLIC_PATHS or not path.startswith(PROTECTED_PREFIXES):
            await self.app(scope, receive, send)
            return
        request = Request(scope)
        if is_authenticated(request):
            await self.app(scope, receive, send)
            return
        response = JSONResponse({"detail": "Login required"}, status_code=401)
        await response(scope, receive, send)
