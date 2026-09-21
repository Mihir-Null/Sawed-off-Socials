"""Who may use the web app.

Two ways in, both producing the same signed session cookie:

* the shared ``APP_PASSWORD`` (subject ``"password"``), or
* "Sign in with Google" as an officer whose email is on the operators list
  (subject = their email).  See ``operators.py``.

The cookie is ``<base64 payload>.<hmac>``.  The payload names the subject and
when it was issued; the HMAC (over a server secret) means nobody can forge or
alter it.  ``HttpOnly`` keeps page scripts away from it, ``SameSite=Lax``
stops other sites from riding on it.  Sessions are re-validated on every
request, so removing an officer from the list logs them out immediately.

When neither a password nor any operators are configured the app is open,
and the UI shows a warning banner.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import threading
import time

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from . import operators
from .config import app_password, env

COOKIE_NAME = "sos_session"
COOKIE_MAX_AGE = 60 * 60 * 24 * 30  # 30 days
PASSWORD_SUBJECT = "password"

# Paths that never need a login (login itself, OAuth callbacks, health).
PUBLIC_PATHS = {
    "/api/health",
    "/api/auth/session",
    "/api/auth/login",
    "/api/auth/google",
    "/api/auth/callback",
    "/api/instagram/callback",
}
PROTECTED_PREFIXES = ("/api/", "/uploads/")

# Random per process unless SOS_SECRET_KEY is set, so sessions survive restarts
# only when the operator opts in.
_SECRET = (env("SOS_SECRET_KEY") or secrets.token_hex(32)).encode()

_fail_lock = threading.Lock()
_failures: dict[str, list[float]] = {}
MAX_FAILURES_PER_MINUTE = 10


# --- Policy -------------------------------------------------------------------

def password_login_enabled() -> bool:
    return app_password() is not None


def auth_required() -> bool:
    return password_login_enabled() or operators.any_configured()


def check_password(candidate: str) -> bool:
    expected = app_password()
    if expected is None:
        return False
    return hmac.compare_digest(candidate.encode(), expected.encode())


# --- Session tokens ---------------------------------------------------------------

def _sign(payload: bytes) -> str:
    return hmac.new(_SECRET, payload, hashlib.sha256).hexdigest()


def make_session(subject: str) -> str:
    payload = base64.urlsafe_b64encode(
        json.dumps({"sub": subject, "iat": int(time.time())}).encode()
    ).decode().rstrip("=")
    return f"{payload}.{_sign(payload.encode())}"


def parse_session(token: str | None) -> str | None:
    """Return the subject of a valid, unexpired token, else ``None``."""
    if not token or "." not in token:
        return None
    payload, sig = token.rsplit(".", 1)
    if not hmac.compare_digest(sig, _sign(payload.encode())):
        return None
    try:
        padded = payload + "=" * (-len(payload) % 4)
        data = json.loads(base64.urlsafe_b64decode(padded))
    except (ValueError, TypeError):
        return None
    if time.time() - float(data.get("iat", 0)) > COOKIE_MAX_AGE:
        return None
    subject = data.get("sub")
    return subject if isinstance(subject, str) and subject else None


def subject_is_valid(subject: str | None) -> bool:
    """A session is only as good as its subject's *current* standing."""
    if subject is None:
        return False
    if subject == PASSWORD_SUBJECT:
        return password_login_enabled()
    return operators.is_operator(subject)


def current_subject(request: Request) -> str | None:
    subject = parse_session(request.cookies.get(COOKIE_NAME))
    return subject if subject_is_valid(subject) else None


def is_authenticated(request: Request) -> bool:
    return not auth_required() or current_subject(request) is not None


# --- Login rate limiting ------------------------------------------------------

def too_many_failures(client_ip: str) -> bool:
    now = time.time()
    with _fail_lock:
        recent = [t for t in _failures.get(client_ip, []) if now - t < 60]
        _failures[client_ip] = recent
        return len(recent) >= MAX_FAILURES_PER_MINUTE


def record_failure(client_ip: str) -> None:
    with _fail_lock:
        _failures.setdefault(client_ip, []).append(time.time())


# --- Middleware ---------------------------------------------------------------

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
        if current_subject(Request(scope)) is not None:
            await self.app(scope, receive, send)
            return
        response = JSONResponse({"detail": "Login required"}, status_code=401)
        await response(scope, receive, send)
