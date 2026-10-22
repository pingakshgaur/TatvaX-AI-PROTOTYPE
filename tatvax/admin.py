"""Teacher dashboard API: class analytics, the content editor (CMS), and feedback."""

import ipaddress
import re
import time
from datetime import date, timedelta
from urllib.parse import urlparse

from flask import Blueprint, current_app, request

from . import gamification, knowledge
from .ai import PROVIDERS, RECOMMENDED_MODELS, AIUnavailable
from .db import get_db, get_setting, now_iso, set_setting, today
from .quiz import subject_scores
from .roles import require_permission
from .security import error
from .users import current_user

bp = Blueprint("admin", __name__, url_prefix="/api/admin")

_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")
_ICON = re.compile(r"^[a-z0-9-]{1,40}$")
_MODEL_ID = re.compile(r"^[A-Za-z0-9._-]+/[A-Za-z0-9._:-]+$")
MAX_BODY_CHARS = 500_000


def _since(days: int) -> str:
    return (date.fromisoformat(today()) - timedelta(days=days - 1)).isoformat()


@bp.get("/overview")
@require_permission("view_analytics")
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
    # Per subject, scoring each subject on its own questions (mixed assessments are split up).
    titles = {d["slug"]: d["title"] for d in knowledge.list_documents(db)}
    per_subject = subject_scores(db.execute(
        "SELECT subject, questions_json, answers_json FROM quizzes WHERE completed_at IS NOT NULL AND total > 0"
    ).fetchall())
    quiz_scores = sorted(
        ({"label": titles.get(slug, slug), "quizzes": len(values), "average": round(sum(values) / len(values))}
         for slug, values in per_subject.items() if values),
        key=lambda row: row["average"],
    )
    return {
        "counts": {**dict(counts), "quiz_average": round(counts["quiz_average"] or 0)},
        "questions_per_day": [{"day": d, "value": per_day.get(d, 0)} for d in days],
        "by_subject": by_subject,
        "by_language": by_language,
        "quiz_scores": quiz_scores,
    }


@bp.get("/students")
@require_permission("view_students")
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
@require_permission("view_feedback")
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
@require_permission("manage_content")
def get_document(slug: str):
    doc = knowledge.get_document(get_db(), slug)
    if doc is None:
        return error("Document not found", 404)
    return {"document": doc}


@bp.post("/documents")
@require_permission("manage_content")
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
@require_permission("manage_content")
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
@require_permission("manage_content")
def delete_document(slug: str):
    db = get_db()
    doc = knowledge.get_document(db, slug)
    if doc is None:
        return error("Document not found", 404)
    if doc["kind"] == "helpdesk" and len(knowledge.list_documents(db, "helpdesk")) == 1:
        return error("TatvAI needs at least one school information page")
    db.execute("DELETE FROM documents WHERE slug = ?", (slug,))
    db.commit()
    return {"ok": True}


# --------------------------------------------------------------------------- AI settings

def _ai():
    return current_app.extensions["tatvax"].ai


def _settings(db) -> dict:
    return {row["key"]: row["value"] for row in db.execute("SELECT key, value FROM settings")}


def _saved_at(db, pid: str):
    key = "nvidia_api_key" if pid == "nvidia" else f"api_key:{pid}"
    row = db.execute("SELECT updated_at FROM settings WHERE key = ?", (key,)).fetchone()
    return row["updated_at"] if row else None


def _ai_settings_response():
    db, ai = get_db(), _ai()
    providers = [{**ai.provider_status(pid), "saved_at": _saved_at(db, pid)} for pid in PROVIDERS]
    return {
        "ai": {**ai.status(), "saved_at": _saved_at(db, ai.active)},
        "active": ai.active,
        "providers": providers,
        "models": RECOMMENDED_MODELS,
    }


def _provider_from(data) -> str:
    pid = str(data.get("provider") or "nvidia")
    if pid not in PROVIDERS:
        raise ValueError("Unknown AI provider")
    return pid


def _blocked_host(url: str) -> bool:
    """Cloud metadata services live on link-local addresses; an AI server address must never point there.
    A local Ollama or a server on the school network (localhost, 192.168.x.x ...) is still allowed."""
    host = (urlparse(url).hostname or "").strip("[]").lower()
    if host in {"metadata", "metadata.google.internal", "metadata.goog"}:
        return True
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return False
    return address.is_link_local or address.is_multicast or address.is_unspecified


@bp.get("/ai")
@require_permission("manage_ai")
def ai_settings():
    return _ai_settings_response()


@bp.put("/ai")
@require_permission("manage_ai")
def update_ai_settings():
    """Save a provider's API key, model and (for Ollama/custom servers) base URL, and optionally make
    it the active provider. An empty api_key removes the saved key. Keys are stored server-side only;
    the API sends back just a short hint unless a teacher explicitly asks to reveal one."""
    data = request.get_json(silent=True) or {}
    try:
        pid = _provider_from(data)
    except ValueError as exc:
        return error(str(exc))
    provider = PROVIDERS[pid]
    db = get_db()
    key_setting = "nvidia_api_key" if pid == "nvidia" else f"api_key:{pid}"
    model_setting = "ai_model" if pid == "nvidia" else f"ai_model:{pid}"

    if "api_key" in data:
        key = str(data["api_key"] or "").strip()
        if key and (len(key) < 8 or any(ch.isspace() for ch in key)):
            hint = f" {provider.name} keys start with '{provider.key_prefix}'." if provider.key_prefix else ""
            return error(f"That doesn't look like a valid API key.{hint}")
        if pid == "nvidia" and key and len(key) < 20:
            return error("That doesn't look like an NVIDIA API key. Keys start with 'nvapi-'.")
        set_setting(db, key_setting, key or None)
    if "model" in data:
        model = str(data["model"] or "").strip()
        if model and not _MODEL_ID.match(model) and not re.match(r"^[A-Za-z0-9._:/-]{2,120}$", model):
            return error("That model ID contains characters that aren't allowed")
        if pid == "nvidia" and model and not _MODEL_ID.match(model):
            return error("Model IDs look like 'publisher/model-name', for example nvidia/nemotron-3-super-120b-a12b")
        set_setting(db, model_setting, model or None)
    if "base_url" in data and pid != "nvidia":
        url = str(data["base_url"] or "").strip()
        if url and not re.match(r"^https?://[^\s]+$", url):
            return error("The server address must start with http:// or https://")
        if url and _blocked_host(url):
            return error("That address isn't allowed. Use the AI server's own address.")
        set_setting(db, f"base_url:{pid}", url or None)
    if data.get("activate"):
        set_setting(db, "ai_provider", pid)
    db.commit()

    ai = _ai()
    ai.load(_settings(db))
    # A new key with no model chosen yet (or a model the provider doesn't offer): pick one that exists.
    if data.get("api_key") and pid != "nvidia" and not data.get("model"):
        chosen = ai.choose_model(pid)
        if chosen and chosen != ai.states[pid].model:
            set_setting(db, model_setting, chosen)
            db.commit()
            ai.load(_settings(db))
    return _ai_settings_response()


@bp.get("/ai/key")
@require_permission("manage_ai")
def reveal_ai_key():
    """The full saved key, shown only when a teacher asks to reveal it in the AI settings tab."""
    ai = _ai()
    pid = request.args.get("provider") or ai.active
    if pid not in PROVIDERS:
        return error("Unknown AI provider")
    state = ai.states[pid]
    if state.source == "environment":
        # Set by whoever runs the server; teachers can replace it here but not read it.
        return {"api_key": None, "source": state.source, "saved_at": None,
                "message": "This key is set on the server (an environment variable), so it can't be shown here."}
    return {"api_key": state.api_key or None, "source": state.source, "saved_at": _saved_at(get_db(), pid)}


@bp.get("/ai/models")
@require_permission("manage_ai")
def list_ai_models():
    pid = request.args.get("provider") or _ai().active
    if pid not in PROVIDERS:
        return error("Unknown AI provider")
    try:
        return {"models": _ai().list_models(pid)}
    except AIUnavailable as exc:
        return error(str(exc).removeprefix("rejected: "), 502)


@bp.post("/ai/test")
@require_permission("manage_ai")
def test_ai():
    data = request.get_json(silent=True) or {}
    try:
        pid = _provider_from({"provider": data.get("provider") or _ai().active})
    except ValueError as exc:
        return error(str(exc))
    started = time.monotonic()
    try:
        reply = _ai().test(pid)
    except AIUnavailable as exc:
        return error(str(exc).removeprefix("rejected: "), 502, ai=_ai().status(), provider=_ai().provider_status(pid))
    return {
        "ok": True,
        "reply": reply[:200],
        "latency_ms": round((time.monotonic() - started) * 1000),
        "ai": _ai().status(),
        "provider": _ai().provider_status(pid),
    }
