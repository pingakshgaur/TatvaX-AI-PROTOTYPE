"""Student-facing JSON API."""

import json
import logging
import re

from flask import Blueprint, Response, current_app, request, stream_with_context

from . import gamification, knowledge, languages, roles, speech
from .db import SCHOOL_TZ, connect, get_db, now_iso, today
from .knowledge import library_index
from .quiz import QuizError, subject_scores
from .security import error, limiter
from .translation import TranslationError
from .users import current_user, public_user

log = logging.getLogger(__name__)
bp = Blueprint("api", __name__, url_prefix="/api")


def services():
    return current_app.extensions["tatvax"]


@bp.get("/health")
def health():
    return {"status": "ok", "ai": services().ai.available}


@bp.get("/bootstrap")
def bootstrap():
    db = get_db()
    ai = services().ai
    helpdesk = knowledge.list_documents(db, "helpdesk")
    return {
        "app": {
            "version": current_app.config["VERSION"],
            "ai_enabled": ai.available,
            "ai_provider": ai.status()["provider"],
            "ai_model": ai.model if ai.available else None,
            "languages": languages.as_list(),
            "subjects": knowledge.list_documents(db, "subject"),
            "helpdesk": helpdesk[0] if helpdesk else None,
            "tts_languages": sorted(code for code in languages.LANGUAGES if code in speech.supported_languages()),
            # Days (due dates, "today", streaks) follow the school's clock, not the device's.
            "today": today(),
            "utc_offset_minutes": int(SCHOOL_TZ.utcoffset(None).total_seconds() // 60),
            # What someone with only the base role may do (before they have a profile).
            "base_permissions": sorted(roles.access(db, None)["permissions"]),
            "demo": bool(current_app.config.get("DEMO_MODE")),
        },
        "user": public_user(current_user()),
    }


# --------------------------------------------------------------------------- chat

_IMAGE = re.compile(r"^data:(image/(?:jpeg|png|webp));base64,([A-Za-z0-9+/=]+)$")
MAX_IMAGE_CHARS = 1_500_000  # base64 characters, about 1.1 MB


@bp.post("/chat")
def chat():
    data = request.get_json(silent=True) or {}
    message = str(data.get("message", "")).strip()
    image = None
    if data.get("image"):
        match = _IMAGE.match(str(data["image"]))
        if not match:
            return error("Photos must be JPEG, PNG or WebP images")
        if len(match.group(2)) > MAX_IMAGE_CHARS:
            return error("That photo is too large. Please try a smaller one.")
        image = {"media_type": match.group(1), "data": match.group(2)}
        message = message or "Please look at this picture and explain it step by step."
    if not message:
        return error("Please type a question")
    if len(message) > current_app.config["MAX_MESSAGE_CHARS"]:
        return error("That message is too long. Please keep it under 2000 characters.")
    mode = data.get("mode", "subject")
    language = languages.normalize(data.get("language"))
    conversation_id = data.get("conversation_id")
    if conversation_id is not None and not isinstance(conversation_id, int):
        return error("Invalid conversation")

    user = current_user(create=True)
    blocked = roles.learning_allowed(get_db(), user, "ask_tutor") or (image and roles.learning_allowed(get_db(), user, "photo_questions"))
    if blocked:
        return error(blocked, 403)
    if not limiter.allow(f"chat:{user['id']}", current_app.config["CHAT_RATE_LIMIT"]):
        return error("You're asking very fast! Take a breath and try again in a minute.", 429)

    # The answer keeps streaming after this view returns, so it gets its own connection.
    conn = connect(current_app.config["DATABASE"])
    events = services().tutor.answer(conn, user, message, mode, data.get("subject"), language, conversation_id, image)
    try:
        first = next(events)  # validation errors surface here, before streaming starts
    except ValueError as exc:
        conn.close()
        return error(str(exc), 404 if "not found" in str(exc) else 400)
    except Exception:
        conn.close()
        raise

    def generate():
        try:
            yield json.dumps(first) + "\n"
            for event in events:
                yield json.dumps(event, ensure_ascii=False) + "\n"
        except Exception:
            log.exception("Chat stream failed")
            yield json.dumps({"type": "error", "message": "Something went wrong. Please try again."}) + "\n"
        finally:
            events.close()
            conn.close()

    return Response(
        stream_with_context(generate()),
        mimetype="application/x-ndjson",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@bp.get("/conversations")
def conversations():
    user = current_user()
    if user is None:
        return {"conversations": []}
    query = "SELECT id, mode, subject, title, updated_at FROM conversations WHERE user_id = ?"
    params: list = [user["id"]]
    if request.args.get("mode"):
        query += " AND mode = ?"
        params.append(request.args["mode"])
    if request.args.get("subject"):
        query += " AND subject = ?"
        params.append(request.args["subject"])
    rows = get_db().execute(query + " ORDER BY updated_at DESC LIMIT 50", params).fetchall()
    return {"conversations": [dict(r) for r in rows]}


def _own_conversation(conversation_id: int):
    user = current_user()
    if user is None:
        return None
    return get_db().execute(
        "SELECT * FROM conversations WHERE id = ? AND user_id = ?", (conversation_id, user["id"])
    ).fetchone()


@bp.get("/conversations/<int:conversation_id>")
def conversation(conversation_id: int):
    convo = _own_conversation(conversation_id)
    if convo is None:
        return error("Conversation not found", 404)
    rows = get_db().execute(
        "SELECT id, role, content, language, engine, suggestions, created_at FROM messages WHERE conversation_id = ? ORDER BY id",
        (conversation_id,),
    ).fetchall()
    messages = []
    for row in rows:
        message = dict(row)
        message["suggestions"] = json.loads(message["suggestions"]) if message["suggestions"] else []
        messages.append(message)
    return {"conversation": dict(convo), "messages": messages}


@bp.post("/conversations/<int:conversation_id>/rewind")
def rewind_conversation(conversation_id: int):
    """Remove a question and everything after it, so an edited question can be asked in its place."""
    if _own_conversation(conversation_id) is None:
        return error("Conversation not found", 404)
    message_id = (request.get_json(silent=True) or {}).get("message_id")
    if not isinstance(message_id, int):
        return error("Send the message_id of the question to edit")
    db = get_db()
    cur = db.execute("DELETE FROM messages WHERE conversation_id = ? AND id >= ?", (conversation_id, message_id))
    db.commit()
    return {"removed": cur.rowcount}


@bp.delete("/conversations/<int:conversation_id>")
def delete_conversation(conversation_id: int):
    if _own_conversation(conversation_id) is None:
        return error("Conversation not found", 404)
    db = get_db()
    db.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
    db.commit()
    return {"ok": True}


# --------------------------------------------------------------------------- quizzes

@bp.post("/quiz")
def create_quiz():
    data = request.get_json(silent=True) or {}
    user = current_user(create=True)
    if blocked := _quiz_blocked(user):
        return blocked
    if _quiz_rate_limited(user):
        return error("That's a lot of quizzes! Please wait a minute before starting another.", 429)
    subjects = data.get("subjects")
    if not isinstance(subjects, list):
        subjects = [str(data.get("subject", ""))]
    try:
        quiz = services().quizmaster.create(
            get_db(), user,
            subjects=[str(s) for s in subjects],
            topic=str(data.get("topic", "")),
            count=data.get("count", 10),
            difficulty=str(data.get("difficulty", "medium")),
            language=languages.normalize(data.get("language")),
            mode=str(data.get("mode", "practice")),
        )
    except QuizError as exc:
        return error(str(exc))
    return {"quiz": quiz}, 201


@bp.post("/quiz/<int:quiz_id>/answer")
def answer_quiz(quiz_id: int):
    data = request.get_json(silent=True) or {}
    user = current_user()
    if user is None:
        return error("Quiz not found", 404)
    index, choice = data.get("index"), data.get("choice")
    if not isinstance(index, int) or not isinstance(choice, int):
        return error("Invalid answer")
    duration = data.get("duration_s")
    try:
        return services().quizmaster.answer(get_db(), user, quiz_id, index, choice,
                                            duration if isinstance(duration, int) else None)
    except QuizError as exc:
        return error(str(exc), 404 if "not found" in str(exc) else 400)


@bp.post("/quiz/<int:quiz_id>/submit")
def submit_quiz(quiz_id: int):
    data = request.get_json(silent=True) or {}
    user = current_user()
    if user is None:
        return error("Quiz not found", 404)
    duration = data.get("duration_s")
    try:
        return services().quizmaster.submit(get_db(), user, quiz_id, data.get("answers"),
                                            duration if isinstance(duration, int) else None)
    except QuizError as exc:
        return error(str(exc), 404 if "not found" in str(exc) else 400)


def _quiz_rate_limited(user) -> bool:
    return not limiter.allow(f"quiz:{user['id']}", 6)


def _quiz_blocked(user):
    """An error response if this learner's roles don't allow starting assessments, else None."""
    message = roles.learning_allowed(get_db(), user, "take_assessments")
    return error(message, 403) if message else None


@bp.post("/quiz/<int:quiz_id>/retry")
def retry_quiz(quiz_id: int):
    user = current_user()
    if user is None:
        return error("Quiz not found", 404)
    if blocked := _quiz_blocked(user):
        return blocked
    if _quiz_rate_limited(user):
        return error("That's a lot of quizzes! Please wait a minute before starting another.", 429)
    try:
        return {"quiz": services().quizmaster.retry_mistakes(get_db(), user, quiz_id)}, 201
    except QuizError as exc:
        return error(str(exc), 404 if "not found" in str(exc) else 400)


@bp.get("/quizzes")
def quiz_history():
    user = current_user()
    if user is None:
        return {"quizzes": []}
    return {"quizzes": services().quizmaster.history(get_db(), user)}


@bp.get("/quiz/<int:quiz_id>")
def quiz_detail(quiz_id: int):
    user = current_user()
    if user is None:
        return error("Quiz not found", 404)
    try:
        return {"quiz": services().quizmaster.detail(get_db(), user, quiz_id)}
    except QuizError as exc:
        return error(str(exc), 404)


@bp.post("/quiz/<int:quiz_id>/retake")
def retake_quiz(quiz_id: int):
    user = current_user()
    if user is None:
        return error("Quiz not found", 404)
    if blocked := _quiz_blocked(user):
        return blocked
    if _quiz_rate_limited(user):
        return error("That's a lot of quizzes! Please wait a minute before starting another.", 429)
    try:
        return {"quiz": services().quizmaster.retake(get_db(), user, quiz_id)}, 201
    except QuizError as exc:
        return error(str(exc), 404)


@bp.delete("/quiz/<int:quiz_id>")
def delete_quiz(quiz_id: int):
    user = current_user()
    if user is None:
        return error("Quiz not found", 404)
    try:
        services().quizmaster.delete(get_db(), user, quiz_id)
    except QuizError as exc:
        return error(str(exc), 404 if "not found" in str(exc) else 409)
    return {"ok": True}


@bp.get("/subjects/overview")
def subjects_overview():
    """Per-subject facts for the Subjects page: size of the notes and the learner's own activity."""
    db = get_db()
    user = current_user()
    scores, last_quiz, read = {}, {}, {}
    if user is not None:
        rows = db.execute("SELECT subject, questions_json, answers_json, completed_at FROM quizzes "
                          "WHERE user_id = ? AND completed_at IS NOT NULL", (user["id"],)).fetchall()
        scores = subject_scores(rows)
        for row in rows:
            for slug in {q.get("subject") or row["subject"] for q in json.loads(row["questions_json"])}:
                last_quiz[slug] = max(last_quiz.get(slug, ""), row["completed_at"])
        read = {r["slug"]: r["n"] for r in db.execute(
            "SELECT slug, COUNT(*) AS n FROM notes_read WHERE user_id = ? GROUP BY slug", (user["id"],))}
    out = []
    for doc in knowledge.list_documents(db, "subject"):
        body = knowledge.get_document(db, doc["slug"])["body"]
        sections = knowledge.split_sections(doc["slug"], doc["title"], body)
        item = {
            "slug": doc["slug"],
            "chapters": sum(1 for line in body.splitlines() if line.startswith("## ")),
            "chapter_titles": [re.sub(r"^Chapter\s+\d+\s*[:.-]\s*", "", line[3:].strip(), flags=re.I)
                               for line in body.splitlines() if line.startswith("## ")][:8],
            "topics": len(sections),
            "questions": 0, "quizzes": 0, "average": None, "last_active": None, "read": 0,
        }
        if user is not None:
            q = db.execute("SELECT COUNT(*), MAX(created_at) FROM question_log WHERE user_id = ? AND subject = ?",
                           (user["id"], doc["slug"])).fetchone()
            mine = scores.get(doc["slug"], [])
            item.update(questions=q[0], quizzes=len(mine), average=round(sum(mine) / len(mine)) if mine else None,
                        last_active=max(filter(None, [q[1], last_quiz.get(doc["slug"])]), default=None),
                        read=read.get(doc["slug"], 0))
        out.append(item)
    return {"subjects": out}


# --------------------------------------------------------------------------- progress

@bp.get("/progress")
def progress():
    user = current_user()
    if user is None:
        return {"progress": None}
    return {"progress": gamification.progress(get_db(), user["id"])}


@bp.get("/leaderboard")
def leaderboard():
    user = current_user()
    if user is None:  # learners' names are only shown to people using the app
        return {"leaderboard": [], "me": None}
    return {"leaderboard": gamification.leaderboard(get_db()), "me": user["id"]}


# --------------------------------------------------------------------------- library

@bp.get("/library")
def library():
    return {"documents": knowledge.list_documents(get_db())}


@bp.get("/library/<slug>")
def library_document(slug: str):
    doc = knowledge.get_document(get_db(), slug)
    if doc is None:
        return error("Document not found", 404)
    doc.pop("updated_by", None)
    return {"document": doc}


_CHAPTER_ID = re.compile(r"^ch-\d{1,4}$")


@bp.get("/library/<slug>/read")
def notes_read(slug: str):
    user = current_user()
    if user is None:
        return {"read": []}
    rows = get_db().execute("SELECT chapter FROM notes_read WHERE user_id = ? AND slug = ?", (user["id"], slug)).fetchall()
    return {"read": [r["chapter"] for r in rows]}


@bp.put("/library/<slug>/read")
def save_notes_read(slug: str):
    """Replace the list of chapters marked as read in one document."""
    db = get_db()
    if knowledge.get_document(db, slug) is None:
        return error("Document not found", 404)
    chapters = (request.get_json(silent=True) or {}).get("read")
    if not isinstance(chapters, list) or len(chapters) > 500 or not all(isinstance(c, str) and _CHAPTER_ID.match(c) for c in chapters):
        return error("Send the chapters read, like [\"ch-0\", \"ch-2\"]")
    user = current_user(create=True)
    db.execute("DELETE FROM notes_read WHERE user_id = ? AND slug = ?", (user["id"], slug))
    db.executemany("INSERT OR IGNORE INTO notes_read (user_id, slug, chapter, read_at) VALUES (?, ?, ?, ?)",
                   [(user["id"], slug, c, now_iso()) for c in chapters])
    db.commit()
    return {"read": sorted(set(chapters), key=lambda c: int(c[3:]))}


@bp.get("/search")
def search():
    query = request.args.get("q", "").strip()[:200]
    if not query:
        return {"results": []}
    slug = request.args.get("subject")
    hits = library_index.search(get_db(), query, [slug] if slug else None, limit=8)
    return {"results": [
        {"slug": s.slug, "title": s.doc_title, "heading": s.heading, "excerpt": s.text[:280], "score": round(score, 2)}
        for s, score in hits
    ]}


# --------------------------------------------------------------------------- language tools

@bp.post("/translate")
def translate():
    data = request.get_json(silent=True) or {}
    text = str(data.get("text", "")).strip()
    if not text:
        return error("Please enter some text")
    if len(text) > 3000:
        return error("Please translate at most 3000 characters at a time")
    user = current_user(create=True)
    if blocked := roles.learning_allowed(get_db(), user, "use_translator"):
        return error(blocked, 403)
    if not limiter.allow(f"translate:{user['id']}", 20):
        return error("Too many translations. Please wait a minute.", 429)
    source = data.get("source", "auto")
    source = languages.detect_language(text) if source == "auto" else languages.normalize(source)
    target = languages.normalize(data.get("target"))
    try:
        translated, engine = services().translator.translate(text, target, source)
    except TranslationError:
        return error("Translation is unavailable right now. Please try again later.", 503)
    return {"text": translated, "engine": engine, "source": source, "target": target}


@bp.post("/tts")
def tts():
    data = request.get_json(silent=True) or {}
    language = languages.normalize(data.get("language"))
    if language not in speech.supported_languages():
        return error("Speech isn't available for this language yet", 422)
    text = speech.clean_for_speech(str(data.get("text", "")))
    if not text:
        return error("Nothing to read aloud")
    user = current_user(create=True)
    if not limiter.allow(f"tts:{user['id']}", 30):
        return error("Too many requests. Please wait a minute.", 429)
    try:
        audio = speech.synthesize(text, language)
    except Exception:
        log.exception("Text-to-speech failed")
        return error("Speech service is unavailable right now", 503)
    return Response(audio, mimetype="audio/mpeg", headers={"Cache-Control": "private, max-age=3600"})


# --------------------------------------------------------------------------- feedback

@bp.post("/feedback")
def feedback():
    data = request.get_json(silent=True) or {}
    message = str(data.get("message", "")).strip()
    if not message:
        return error("Please write a message")
    rating = data.get("rating")
    if rating is not None and (not isinstance(rating, int) or not 1 <= rating <= 5):
        return error("Rating must be between 1 and 5")
    user = current_user(create=True)
    if not limiter.allow(f"feedback:{user['id']}", 5):
        return error("Thanks! You've sent a lot of feedback already. Please try again later.", 429)
    db = get_db()
    db.execute(
        "INSERT INTO feedback (user_id, rating, name, email, message, page, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (user["id"], rating, str(data.get("name", ""))[:80] or None, str(data.get("email", ""))[:120] or None,
         message[:3000], str(data.get("page", ""))[:120] or None, now_iso()),
    )
    db.commit()
    return {"ok": True}, 201
