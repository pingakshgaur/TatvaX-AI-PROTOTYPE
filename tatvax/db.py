"""SQLite storage. One connection per request, WAL mode so streaming answers don't block readers."""

import os
import sqlite3
from datetime import datetime, timedelta, timezone

from flask import current_app, g

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL DEFAULT 'Learner',
    email TEXT UNIQUE,
    password_hash TEXT,
    role TEXT NOT NULL DEFAULT 'student',          -- student | teacher
    is_guest INTEGER NOT NULL DEFAULT 1,
    language TEXT NOT NULL DEFAULT 'en',
    grade INTEGER,                                 -- school class 1-12, optional
    theme TEXT NOT NULL DEFAULT 'system',
    leaderboard INTEGER NOT NULL DEFAULT 1,        -- show on the class leaderboard
    xp INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    last_seen TEXT
);

CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    mode TEXT NOT NULL,                            -- subject | helpdesk
    subject TEXT,                                  -- document slug
    title TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id, updated_at);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY,
    conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL,                            -- user | assistant
    content TEXT NOT NULL,
    api_content TEXT,                              -- exact prompt sent to the AI model, replayed as history
    language TEXT NOT NULL DEFAULT 'en',
    engine TEXT,                                   -- ai | library (assistant messages)
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id, id);

CREATE TABLE IF NOT EXISTS quizzes (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    subject TEXT NOT NULL,
    topic TEXT,
    language TEXT NOT NULL,
    difficulty TEXT NOT NULL DEFAULT 'medium',
    questions_json TEXT NOT NULL,
    answers_json TEXT,
    score INTEGER,
    total INTEGER NOT NULL,
    engine TEXT NOT NULL,
    created_at TEXT NOT NULL,
    completed_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_quizzes_user ON quizzes(user_id, created_at);

CREATE TABLE IF NOT EXISTS activity (
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    day TEXT NOT NULL,
    questions INTEGER NOT NULL DEFAULT 0,
    quizzes INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, day)
);

CREATE TABLE IF NOT EXISTS question_log (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    mode TEXT NOT NULL,
    subject TEXT,
    language TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_question_log_time ON question_log(created_at);
CREATE INDEX IF NOT EXISTS idx_question_log_user ON question_log(user_id);

CREATE TABLE IF NOT EXISTS xp_events (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    reason TEXT NOT NULL,
    points INTEGER NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_xp_user_time ON xp_events(user_id, created_at);

CREATE TABLE IF NOT EXISTS badges (
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    badge TEXT NOT NULL,
    earned_at TEXT NOT NULL,
    PRIMARY KEY (user_id, badge)
);

CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    rating INTEGER,
    name TEXT,
    email TEXT,
    message TEXT NOT NULL,
    page TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS todos (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    notes TEXT,
    done INTEGER NOT NULL DEFAULT 0,
    priority TEXT NOT NULL DEFAULT 'medium',     -- low | medium | high | urgent
    due_date TEXT,                               -- YYYY-MM-DD
    subject TEXT,                                -- document slug
    tags TEXT,                                   -- JSON list
    subtasks TEXT,                               -- JSON list of {text, done}
    position INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    completed_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_todos_user ON todos(user_id, done, position);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY,
    slug TEXT NOT NULL UNIQUE,
    kind TEXT NOT NULL,                            -- subject | helpdesk
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    icon TEXT NOT NULL DEFAULT 'book',
    color TEXT NOT NULL DEFAULT '#2563eb',
    position INTEGER NOT NULL DEFAULT 100,
    body TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    updated_by INTEGER REFERENCES users(id) ON DELETE SET NULL
);
"""


# Days (streaks, daily goals, due dates, "today" in reports) follow the school's clock, not UTC.
# India by default; set TATVAX_UTC_OFFSET_MINUTES for schools elsewhere (for example 0 or -300).
SCHOOL_TZ = timezone(timedelta(minutes=int(os.environ.get("TATVAX_UTC_OFFSET_MINUTES", "330"))))


def now_iso() -> str:
    return datetime.now(SCHOOL_TZ).isoformat(timespec="seconds")


def today() -> str:
    return datetime.now(SCHOOL_TZ).date().isoformat()


def connect(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path, timeout=15, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 15000")
    return conn


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = connect(current_app.config["DATABASE"])
    return g.db


def close_db(_exc=None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


# Columns added after the first release. Each is added once, so existing databases upgrade in place.
MIGRATIONS = [
    ("messages", "suggestions", "TEXT"),                         # JSON list of follow-up questions
    ("users", "daily_goal", "INTEGER NOT NULL DEFAULT 5"),       # learning actions per day
    ("quizzes", "subjects_json", "TEXT"),                        # JSON list of subject slugs
    ("quizzes", "mode", "TEXT NOT NULL DEFAULT 'practice'"),     # practice | exam | timed
    ("quizzes", "time_limit", "INTEGER"),                        # seconds, timed mode
    ("quizzes", "duration_s", "INTEGER"),                        # seconds taken
]


def migrate(conn) -> None:
    for table, column, declaration in MIGRATIONS:
        columns = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
        if column not in columns:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {declaration}")
    # v2.5.1: the help desk became TatvAI, so its notes are now called "School Information".
    conn.execute("UPDATE documents SET title = 'School Information' WHERE slug = 'school-faq' AND title = 'School Help Desk'")


def init_db(path: str) -> None:
    conn = connect(path)
    try:
        conn.executescript(SCHEMA)
        migrate(conn)
        conn.commit()
    finally:
        conn.close()


def row_to_dict(row) -> dict | None:
    return dict(row) if row is not None else None


def get_setting(conn, key: str) -> str | None:
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else None


def set_setting(conn, key: str, value: str | None) -> None:
    if value is None:
        conn.execute("DELETE FROM settings WHERE key = ?", (key,))
    else:
        conn.execute(
            """INSERT INTO settings (key, value, updated_at) VALUES (?, ?, ?)
               ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at""",
            (key, value, now_iso()),
        )
