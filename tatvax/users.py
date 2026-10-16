"""Accounts. Every visitor gets a guest profile on first use; registering upgrades it in
place and logging in merges guest progress into the existing account."""

import re

from flask import Blueprint, current_app, request, session
from werkzeug.security import check_password_hash, generate_password_hash

from . import languages
from .db import get_db, now_iso
from .gamification import level_info
from .security import client_ip, error, limiter

bp = Blueprint("users", __name__, url_prefix="/api")

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
THEMES = {"system", "light", "dark", "saffron", "contrast"}


def current_user(create: bool = False):
    db = get_db()
    uid = session.get("uid")
    user = db.execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone() if uid else None
    if user is None and create:
        cur = db.execute(
            "INSERT INTO users (name, is_guest, created_at, last_seen) VALUES ('Learner', 1, ?, ?)",
            (now_iso(), now_iso()),
        )
        db.commit()
        session.clear()
        session.permanent = True
        session["uid"] = cur.lastrowid
        user = db.execute("SELECT * FROM users WHERE id = ?", (cur.lastrowid,)).fetchone()
    return user


def public_user(user) -> dict | None:
    if user is None:
        return None
    return {
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
        "role": user["role"],
        "is_guest": bool(user["is_guest"]),
        "language": user["language"],
        "grade": user["grade"],
        "theme": user["theme"],
        "leaderboard": bool(user["leaderboard"]),
        "daily_goal": user["daily_goal"],
        **level_info(user["xp"]),
    }


def _merge_guest_into(db, guest_id: int, user_id: int) -> None:
    """Move a guest's conversations, quizzes and progress onto a real account."""
    if guest_id == user_id:
        return
    for table in ("conversations", "quizzes", "question_log", "xp_events", "todos"):
        db.execute(f"UPDATE {table} SET user_id = ? WHERE user_id = ?", (user_id, guest_id))
    # Review cards are unique per question, so a card the account already has wins.
    db.execute("UPDATE OR IGNORE review_cards SET user_id = ? WHERE user_id = ?", (user_id, guest_id))
    db.execute("DELETE FROM review_cards WHERE user_id = ?", (guest_id,))
    db.execute(
        """INSERT INTO activity (user_id, day, questions, quizzes)
           SELECT ?, day, questions, quizzes FROM activity WHERE user_id = ?
           ON CONFLICT(user_id, day) DO UPDATE SET questions = questions + excluded.questions,
                                                   quizzes = quizzes + excluded.quizzes""",
        (user_id, guest_id),
    )
    db.execute(
        "INSERT OR IGNORE INTO badges (user_id, badge, earned_at) SELECT ?, badge, earned_at FROM badges WHERE user_id = ?",
        (user_id, guest_id),
    )
    db.execute(
        "UPDATE users SET xp = (SELECT COALESCE(SUM(points), 0) FROM xp_events WHERE user_id = ?) WHERE id = ?",
        (user_id, user_id),
    )
    db.execute("DELETE FROM users WHERE id = ? AND is_guest = 1", (guest_id,))


def _login(user_id: int) -> None:
    session.clear()
    session.permanent = True
    session["uid"] = user_id


@bp.get("/me")
def me():
    return {"user": public_user(current_user())}


@bp.patch("/me")
def update_me():
    user = current_user(create=True)
    data = request.get_json(silent=True) or {}
    updates = {}
    if "name" in data:
        name = str(data["name"]).strip()[:40]
        if not name:
            return error("Name can't be empty")
        updates["name"] = name
    if "language" in data:
        if not languages.is_supported(data["language"]):
            return error("Unsupported language")
        updates["language"] = data["language"]
    if "grade" in data:
        grade = data["grade"]
        if grade in (None, ""):
            updates["grade"] = None
        elif isinstance(grade, int) and 1 <= grade <= 12:
            updates["grade"] = grade
        else:
            return error("Class must be between 1 and 12")
    if "theme" in data:
        if data["theme"] not in THEMES:
            return error("Unknown theme")
        updates["theme"] = data["theme"]
    if "leaderboard" in data:
        updates["leaderboard"] = 1 if data["leaderboard"] else 0
    if "daily_goal" in data:
        goal = data["daily_goal"]
        if not isinstance(goal, int) or not 1 <= goal <= 50:
            return error("Daily goal must be between 1 and 50")
        updates["daily_goal"] = goal
    if updates:
        db = get_db()
        assignments = ", ".join(f"{column} = ?" for column in updates)
        db.execute(f"UPDATE users SET {assignments} WHERE id = ?", (*updates.values(), user["id"]))
        db.commit()
    return {"user": public_user(current_user())}


@bp.post("/auth/register")
def register():
    if not limiter.allow(f"auth:{client_ip()}", 10):
        return error("Too many attempts. Please wait a minute.", 429)
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()[:40]
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))
    if not name:
        return error("Please enter your name")
    if not _EMAIL.match(email):
        return error("Please enter a valid email address")
    if len(password) < 8:
        return error("Password must be at least 8 characters")

    db = get_db()
    if db.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone():
        return error("An account with this email already exists", 409)

    # The first account on a fresh install becomes the teacher/admin. After that, teacher
    # accounts need the TATVAX_TEACHER_CODE.
    has_registered = db.execute("SELECT 1 FROM users WHERE is_guest = 0 LIMIT 1").fetchone()
    teacher_code = current_app.config["TEACHER_CODE"]
    role = "student"
    if not has_registered:
        role = "teacher"
    elif data.get("teacher_code"):
        if not teacher_code or data["teacher_code"] != teacher_code:
            return error("That teacher code isn't valid")
        role = "teacher"

    user = current_user(create=True)
    language = data.get("language") if languages.is_supported(data.get("language")) else user["language"]
    db.execute(
        """UPDATE users SET name = ?, email = ?, password_hash = ?, role = ?, is_guest = 0, language = ?
           WHERE id = ?""",
        (name, email, generate_password_hash(password), role, language, user["id"]),
    )
    db.commit()
    _login(user["id"])
    return {"user": public_user(current_user())}, 201


@bp.post("/auth/login")
def login():
    if not limiter.allow(f"auth:{client_ip()}", 10):
        return error("Too many attempts. Please wait a minute.", 429)
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))
    db = get_db()
    account = db.execute("SELECT * FROM users WHERE email = ? AND is_guest = 0", (email,)).fetchone()
    if account is None or not check_password_hash(account["password_hash"] or "", password):
        return error("Email or password is incorrect", 401)

    guest = current_user()
    if guest is not None and guest["is_guest"]:
        _merge_guest_into(db, guest["id"], account["id"])
    db.execute("UPDATE users SET last_seen = ? WHERE id = ?", (now_iso(), account["id"]))
    db.commit()
    _login(account["id"])
    return {"user": public_user(current_user())}


@bp.post("/auth/logout")
def logout():
    session.clear()
    return {"ok": True}
