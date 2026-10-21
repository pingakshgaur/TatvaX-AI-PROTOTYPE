"""Request guards: JSON-only writes (a CSRF defence), rate limiting, and role checks."""

import sqlite3
import threading
import time
from collections import defaultdict, deque
from functools import wraps

from flask import jsonify, request


def error(message: str, status: int = 400, **extra):
    return jsonify({"error": message, **extra}), status


class RateLimiter:
    """Sliding-window rate limits. In memory by default, which suits one server process. With
    TATVAX_SHARED_RATE_LIMIT=1 the counts live in the database instead, so several worker processes
    (for example gunicorn -w 4) share the same limits."""

    def __init__(self):
        self._hits: dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()
        self._database: str | None = None
        self._local = threading.local()
        self._calls = 0

    def configure(self, database: str | None) -> None:
        self._database = database
        if database:
            conn = self._conn()
            conn.execute("CREATE TABLE IF NOT EXISTS rate_hits (key TEXT NOT NULL, at REAL NOT NULL)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_rate_hits ON rate_hits(key, at)")
            conn.commit()

    def _conn(self):
        conn = getattr(self._local, "conn", None)
        if conn is None or getattr(self._local, "path", None) != self._database:
            conn = sqlite3.connect(self._database, timeout=15, check_same_thread=False, isolation_level=None)
            conn.execute("PRAGMA journal_mode = WAL")
            self._local.conn, self._local.path = conn, self._database
        return conn

    def allow(self, key: str, limit: int, window: float = 60.0) -> bool:
        if self._database:
            return self._allow_shared(key, limit, window)
        now = time.monotonic()
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] > window:
                hits.popleft()
            if len(hits) >= limit:
                return False
            hits.append(now)
            return True

    def _allow_shared(self, key: str, limit: int, window: float) -> bool:
        now = time.time()
        conn = self._conn()
        try:
            conn.execute("BEGIN IMMEDIATE")  # one process at a time, so two can't both take the last slot
            conn.execute("DELETE FROM rate_hits WHERE key = ? AND at < ?", (key, now - window))
            self._calls += 1
            if self._calls % 200 == 0:  # now and then, drop old hits of keys nobody has used lately
                conn.execute("DELETE FROM rate_hits WHERE at < ?", (now - 3600,))
            count = conn.execute("SELECT COUNT(*) FROM rate_hits WHERE key = ?", (key,)).fetchone()[0]
            allowed = count < limit
            if allowed:
                conn.execute("INSERT INTO rate_hits (key, at) VALUES (?, ?)", (key, now))
            conn.commit()
            return allowed
        except sqlite3.Error:
            conn.rollback()
            return True  # never lock learners out because the limiter itself failed

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()
        if self._database:
            self._conn().execute("DELETE FROM rate_hits")
            self._conn().commit()


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
