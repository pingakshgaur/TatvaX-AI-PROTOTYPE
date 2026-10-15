"""Request guards: JSON-only writes (a CSRF defence), rate limiting, and role checks."""

import threading
import time
from collections import defaultdict, deque
from functools import wraps

from flask import jsonify, request


def error(message: str, status: int = 400, **extra):
    return jsonify({"error": message, **extra}), status


class RateLimiter:
    """In-memory sliding window. Good enough for a single-process deployment."""

    def __init__(self):
        self._hits: dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str, limit: int, window: float = 60.0) -> bool:
        now = time.monotonic()
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] > window:
                hits.popleft()
            if len(hits) >= limit:
                return False
            hits.append(now)
            return True

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


limiter = RateLimiter()


def require_json_for_writes():
    """Registered as a before_request hook for /api.

    A cross-site page can only send "simple" requests without a CORS preflight: GET, HEAD and
    POST with form-style bodies. This app never approves a preflight, so PUT/PATCH/DELETE are
    already same-origin only, and requiring JSON on POST closes the remaining CSRF route."""
    if request.method == "POST" and request.path.startswith("/api/") and not request.is_json:
        return error("Requests must be sent as JSON", 415)
    return None


def client_ip() -> str:
    # Behind a reverse proxy, set TATVAX_BEHIND_PROXY=1 so ProxyFix fills remote_addr correctly.
    return request.remote_addr or "unknown"


def require_role(*roles):
    def decorator(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            from .users import current_user

            user = current_user()
            if user is None or user["is_guest"]:
                return error("Please sign in first", 401)
            if roles and user["role"] not in roles:
                return error("You don't have access to this page", 403)
            return view(*args, **kwargs)

        return wrapper

    return decorator
