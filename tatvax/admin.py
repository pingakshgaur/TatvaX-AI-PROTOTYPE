"""Teacher dashboard API: class analytics, the content editor (CMS), and feedback."""

import re
from datetime import date, timedelta

import time

from flask import Blueprint, current_app, request

from . import gamification, knowledge
from .ai import RECOMMENDED_MODELS, AIUnavailable
from .db import get_db, get_setting, now_iso, set_setting, today
from .security import error, require_role
from .users import current_user

bp = Blueprint("admin", __name__, url_prefix="/api/admin")

_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")
_ICON = re.compile(r"^[a-z0-9-]{1,40}$")
_MODEL_ID = re.compile(r"^[A-Za-z0-9._-]+/[A-Za-z0-9._:-]+$")
MAX_BODY_CHARS = 500_000


def _since(days: int) -> str:
    return (date.fromisoformat(today()) - timedelta(days=days - 1)).isoformat()


@bp.get("/overview")
@require_role("teacher")
def overview():
    db = get_db()
    week = _since(7)
    counts = db.execute(
        """SELECT
             (SELECT COUNT(*) FROM users WHERE is_guest = 0 AND role = 'student') AS students,
             (SELECT COUNT(*) FROM users WHERE is_guest = 1) AS guests,
             (SELECT COUNT(*) FROM question_log) AS questions,
             (SELECT COUNT(*) FROM question_log WHERE created_at >= ?) AS questions_week,
             (SELECT COUNT(DISTINCT user_id) FROM question_log WHERE created_at >= ?) AS active_week,
             (SELECT COUNT(*) FROM quizzes WHERE completed_at IS NOT NULL) AS quizzes,
             (SELECT AVG(100.0 * score / total) FROM quizzes WHERE completed_at IS NOT NULL) AS quiz_average""",
        (week, week),
    ).fetchone()

    per_day = {r["day"]: r["n"] for r in db.execute(
        "SELECT substr(created_at, 1, 10) AS day, COUNT(*) AS n FROM question_log WHERE created_at >= ? GROUP BY day",
        (_since(14),),
    )}
    days = [(date.fromisoformat(_since(14)) + timedelta(days=i)).isoformat() for i in range(14)]

    by_subject = [dict(r) for r in db.execute(
        """SELECT CASE WHEN q.mode = 'helpdesk' THEN 'Help desk' ELSE COALESCE(d.title, 'All subjects') END AS label,
                  COUNT(*) AS value
           FROM question_log q LEFT JOIN documents d ON d.slug = q.subject
           GROUP BY label ORDER BY value DESC"""
    )]
    by_language = [dict(r) for r in db.execute(
        "SELECT language AS label, COUNT(*) AS value FROM question_log GROUP BY language ORDER BY value DESC"
    )]
    quiz_scores = [dict(r) for r in db.execute(
        """SELECT COALESCE(d.title, q.subject) AS label, COUNT(*) AS quizzes,
                  ROUND(AVG(100.0 * q.score / q.total)) AS average
           FROM quizzes q LEFT JOIN documents d ON d.slug = q.subject
           WHERE q.completed_at IS NOT NULL GROUP BY q.subject ORDER BY average"""
    )]
    return {
        "counts": {**dict(counts), "quiz_average": round(counts["quiz_average"] or 0)},
        "questions_per_day": [{"day": d, "value": per_day.get(d, 0)} for d in days],
        "by_subject": by_subject,
        "by_language": by_language,
        "quiz_scores": quiz_scores,
    }


@bp.get("/students")
@require_role("teacher")
def students():
    rows = get_db().execute(
        """SELECT u.id, u.name, u.email, u.grade, u.xp, u.created_at,
                  (SELECT COUNT(*) FROM question_log q WHERE q.user_id = u.id) AS questions,
                  (SELECT COUNT(*) FROM quizzes z WHERE z.user_id = u.id AND z.completed_at IS NOT NULL) AS quizzes,
                  (SELECT ROUND(AVG(100.0 * z.score / z.total)) FROM quizzes z
                     WHERE z.user_id = u.id AND z.completed_at IS NOT NULL) AS quiz_average,
                  (SELECT MAX(day) FROM activity a WHERE a.user_id = u.id) AS last_active
           FROM users u WHERE u.is_guest = 0 AND u.role = 'student'
           ORDER BY u.xp DESC LIMIT 500"""
    ).fetchall()
    return {"students": [{**dict(r), "level": gamification.level_info(r["xp"])["level"]} for r in rows]}


@bp.get("/feedback")
@require_role("teacher")
def feedback():
    rows = get_db().execute(
        "SELECT id, rating, name, email, message, page, created_at FROM feedback ORDER BY id DESC LIMIT 200"
    ).fetchall()
    return {"feedback": [dict(r) for r in rows]}


# --------------------------------------------------------------------------- content editor

def _validate_document(data: dict, partial: bool) -> tuple[dict, str | None]:
    clean = {}
    if "title" in data or not partial:
        title = str(data.get("title", "")).strip()[:80]
        if not title:
            return {}, "Title is required"
        clean["title"] = title
    if "description" in data:
        clean["description"] = str(data["description"]).strip()[:200]
    if "icon" in data:
        if not _ICON.match(str(data["icon"])):
            return {}, "Icon must be a Lucide icon name like 'book-open'"
        clean["icon"] = data["icon"]
    if "color" in data:
        if not _COLOR.match(str(data["color"])):
            return {}, "Colour must look like #2563eb"
        clean["color"] = data["color"]
    if "position" in data:
        if not isinstance(data["position"], int):
            return {}, "Position must be a number"
        clean["position"] = data["position"]
    if "body" in data or not partial:
        body = str(data.get("body", "")).replace("\r\n", "\n")
        if len(body.strip()) < 20:
            return {}, "Please write some notes (at least a few sentences)"
        if len(body) > MAX_BODY_CHARS:
            return {}, "These notes are too long. Please split them into several subjects."
        clean["body"] = body
    return clean, None


@bp.get("/documents/<slug>")
@require_role("teacher")
def get_document(slug: str):
    doc = knowledge.get_document(get_db(), slug)
    if doc is None:
        return error("Document not found", 404)
    return {"document": doc}


@bp.post("/documents")
@require_role("teacher")
def create_document():
    data = request.get_json(silent=True) or {}
    kind = data.get("kind", "subject")
    if kind not in ("subject", "helpdesk"):
        return error("Unknown document type")
    clean, problem = _validate_document(data, partial=False)
    if problem:
        return error(problem)
    db = get_db()
    base = knowledge.slugify(clean["title"])
    slug, n = base, 2
    while db.execute("SELECT 1 FROM documents WHERE slug = ?", (slug,)).fetchone():
        slug, n = f"{base}-{n}", n + 1
    db.execute(
        """INSERT INTO documents (slug, kind, title, description, icon, color, position, body, updated_at, updated_by)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (slug, kind, clean["title"], clean.get("description", ""), clean.get("icon", "book"),
         clean.get("color", "#2563eb"), clean.get("position", 100), clean["body"], now_iso(), current_user()["id"]),
    )
    db.commit()
    return {"document": knowledge.get_document(db, slug)}, 201


@bp.put("/documents/<slug>")
@require_role("teacher")
def update_document(slug: str):
    db = get_db()
    if knowledge.get_document(db, slug) is None:
        return error("Document not found", 404)
    clean, problem = _validate_document(request.get_json(silent=True) or {}, partial=True)
    if problem:
        return error(problem)
    if clean:
        clean.update(updated_at=now_iso(), updated_by=current_user()["id"])
        assignments = ", ".join(f"{column} = ?" for column in clean)
        db.execute(f"UPDATE documents SET {assignments} WHERE slug = ?", (*clean.values(), slug))
        db.commit()
    return {"document": knowledge.get_document(db, slug)}


@bp.delete("/documents/<slug>")
@require_role("teacher")
def delete_document(slug: str):
    db = get_db()
    doc = knowledge.get_document(db, slug)
    if doc is None:
        return error("Document not found", 404)
    if doc["kind"] == "helpdesk" and len(knowledge.list_documents(db, "helpdesk")) == 1:
        return error("The help desk needs at least one information page")
    db.execute("DELETE FROM documents WHERE slug = ?", (slug,))
    db.commit()
    return {"ok": True}


# --------------------------------------------------------------------------- AI settings

def _ai():
    return current_app.extensions["tatvax"].ai


def _ai_settings_response():
    return {"ai": _ai().status(), "models": RECOMMENDED_MODELS}


@bp.get("/ai")
@require_role("teacher")
def ai_settings():
    return _ai_settings_response()


@bp.put("/ai")
@require_role("teacher")
def update_ai_settings():
    """Save the NVIDIA API key and/or model. An empty api_key removes the saved key.

    The key is stored server-side only; the API never sends it back, just a short hint."""
    data = request.get_json(silent=True) or {}
    db = get_db()
    if "api_key" in data:
        key = str(data["api_key"] or "").strip()
        if key and (len(key) < 20 or any(ch.isspace() for ch in key)):
            return error("That doesn't look like an NVIDIA API key. Keys start with 'nvapi-'.")
        set_setting(db, "nvidia_api_key", key or None)
    if "model" in data:
        model = str(data["model"] or "").strip()
        if model and not _MODEL_ID.match(model):
            return error("Model IDs look like 'publisher/model-name', for example google/gemma-4-31b-it")
        set_setting(db, "ai_model", model or None)
    db.commit()
    _ai().configure(get_setting(db, "nvidia_api_key"), get_setting(db, "ai_model"))
    return _ai_settings_response()


@bp.post("/ai/test")
@require_role("teacher")
def test_ai():
    started = time.monotonic()
    try:
        reply = _ai().test()
    except AIUnavailable as exc:
        return error(str(exc).removeprefix("rejected: "), 502, ai=_ai().status())
    return {
        "ok": True,
        "reply": reply[:200],
        "latency_ms": round((time.monotonic() - started) * 1000),
        "ai": _ai().status(),
    }
