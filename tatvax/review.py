"""Spaced repetition. Every question a learner gets wrong in an assessment becomes a review card.
Cards move through Leitner boxes: a correct answer sends a card to the next box and a longer gap
before it returns; a wrong answer sends it back to the start. Box 5 means mastered."""

import json
import re
from datetime import date, timedelta

from flask import Blueprint, request

from . import gamification
from .db import get_db, now_iso, today
from .security import error
from .users import current_user

bp = Blueprint("review", __name__, url_prefix="/api/review")

INTERVALS = [0, 1, 3, 7, 16, 35]   # days until a card in each box is due again
MASTERED = len(INTERVALS) - 1
REVIEW_XP = 2                       # per correct review
REVIEW_XP_DAILY_CAP = 40
SESSION_SIZE = 20


def _fingerprint(question: str) -> str:
    return re.sub(r"\W+", " ", question.lower()).strip()[:300]


def _due_after(box: int) -> str:
    return (date.fromisoformat(today()) + timedelta(days=INTERVALS[box])).isoformat()


def add_missed(conn, user_id: int, questions: list[dict], answers: dict) -> int:
    """Called when an assessment is finished: every wrong or skipped question becomes (or resets) a card."""
    added = 0
    for i, q in enumerate(questions):
        if answers.get(str(i)) == q.get("answer_index"):
            continue
        card = {k: q.get(k) for k in ("question", "options", "answer_index", "explanation", "subject_title")}
        cur = conn.execute(
            """INSERT INTO review_cards (user_id, fingerprint, subject, card_json, box, due, created_at)
               VALUES (?, ?, ?, ?, 0, ?, ?)
               ON CONFLICT(user_id, fingerprint) DO UPDATE SET box = 0, due = excluded.due, card_json = excluded.card_json""",
            (user_id, _fingerprint(q["question"]), q.get("subject"), json.dumps(card, ensure_ascii=False), today(), now_iso()),
        )
        added += cur.rowcount
    return added


def _public(row) -> dict:
    card = json.loads(row["card_json"])
    return {
        "id": row["id"], "subject": row["subject"], "subject_title": card.get("subject_title"),
        "question": card["question"], "options": card["options"],
        "box": row["box"], "due": row["due"], "reviews": row["reviews"], "lapses": row["lapses"],
    }


def summary(conn, user_id: int) -> dict:
    rows = conn.execute("SELECT box, due FROM review_cards WHERE user_id = ?", (user_id,)).fetchall()
    day = today()
    upcoming = sorted(r["due"] for r in rows if r["due"] > day and r["box"] < MASTERED)
    return {
        "total": len(rows),
        "due": sum(1 for r in rows if r["due"] <= day and r["box"] < MASTERED),
        "mastered": sum(1 for r in rows if r["box"] >= MASTERED),
        "boxes": [sum(1 for r in rows if r["box"] == b) for b in range(MASTERED + 1)],
        "next_due": upcoming[0] if upcoming else None,
    }


@bp.get("")
def due_cards():
    user = current_user()
    if user is None:
        return {"cards": [], "summary": {"total": 0, "due": 0, "mastered": 0, "boxes": [0] * (MASTERED + 1), "next_due": None}}
    db = get_db()
    subject = request.args.get("subject")
    query = "SELECT * FROM review_cards WHERE user_id = ? AND due <= ? AND box < ?"
    params: list = [user["id"], today(), MASTERED]
    if subject:
        query += " AND subject = ?"
        params.append(subject)
    rows = db.execute(query + " ORDER BY box, due, id LIMIT ?", (*params, SESSION_SIZE)).fetchall()
    return {"cards": [_public(r) for r in rows], "summary": summary(db, user["id"])}


@bp.get("/all")
def all_cards():
    user = current_user()
    if user is None:
        return {"cards": []}
    rows = get_db().execute("SELECT * FROM review_cards WHERE user_id = ? ORDER BY due, box, id", (user["id"],)).fetchall()
    return {"cards": [_public(r) for r in rows]}


@bp.post("/<int:card_id>")
def answer_card(card_id: int):
    user = current_user()
    db = get_db()
    row = db.execute("SELECT * FROM review_cards WHERE id = ? AND user_id = ?", (card_id, user["id"] if user else -1)).fetchone()
    if row is None:
        return error("Card not found", 404)
    choice = (request.get_json(silent=True) or {}).get("choice")
    if not isinstance(choice, int) or not 0 <= choice < 4:
        return error("Choose one of the four answers")
    card = json.loads(row["card_json"])
    correct = choice == card["answer_index"]
    box = min(MASTERED, row["box"] + 1) if correct else 0
    due = _due_after(box) if correct else _due_after(1)
    db.execute(
        """UPDATE review_cards SET box = ?, due = ?, reviews = reviews + 1, lapses = lapses + ?, reviewed_at = ?
           WHERE id = ?""",
        (box, due, 0 if correct else 1, now_iso(), card_id),
    )
    xp = 0
    if correct:
        earned = db.execute(
            "SELECT COALESCE(SUM(points), 0) FROM xp_events WHERE user_id = ? AND reason = 'review' AND created_at >= ?",
            (user["id"], today()),
        ).fetchone()[0]
        if earned < REVIEW_XP_DAILY_CAP:
            xp = gamification.award_xp(db, user["id"], "review", REVIEW_XP)
    db.commit()
    return {
        "correct": correct, "answer_index": card["answer_index"], "explanation": card.get("explanation"),
        "box": box, "due": due, "mastered": box >= MASTERED, "xp_gained": xp, "summary": summary(db, user["id"]),
    }


@bp.delete("/<int:card_id>")
def delete_card(card_id: int):
    user = current_user()
    db = get_db()
    cur = db.execute("DELETE FROM review_cards WHERE id = ? AND user_id = ?", (card_id, user["id"] if user else -1))
    db.commit()
    if not cur.rowcount:
        return error("Card not found", 404)
    return {"ok": True}
