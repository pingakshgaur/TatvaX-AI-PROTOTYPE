"""Work set by teachers. An assessment assignment has its questions written once, so every student
in the class answers the same questions (reshuffled); a reading assignment points at study notes and
is ticked off by the student. Teachers see who has finished and how they scored."""

import json
import random
import re

from flask import Blueprint, current_app, request

from . import knowledge, languages
from .db import get_db, now_iso, today
from .quiz import MODES, QuizError, _shuffle_options
from .security import error, require_role
from .users import current_user

student_bp = Blueprint("assignments", __name__, url_prefix="/api/assignments")
teacher_bp = Blueprint("admin_assignments", __name__, url_prefix="/api/admin/assignments")

_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _quizmaster():
    return current_app.extensions["tatvax"].quizmaster


def _subjects(conn, row) -> list[dict]:
    slugs = json.loads(row["subjects_json"])
    docs = [knowledge.get_document(conn, s) for s in slugs]
    return [{"slug": d["slug"], "title": d["title"], "color": d["color"]} for d in docs if d]


def _public(conn, row) -> dict:
    questions = json.loads(row["questions_json"]) if row["questions_json"] else []
    return {
        "id": row["id"], "title": row["title"], "instructions": row["instructions"], "kind": row["kind"],
        "subjects": _subjects(conn, row), "topic": row["topic"], "grade": row["grade"], "mode": row["mode"],
        "difficulty": row["difficulty"], "language": row["language"], "questions": len(questions),
        "due_date": row["due_date"], "archived": bool(row["archived"]), "created_at": row["created_at"],
    }


def _for_student(user) -> str:
    """SQL condition for the assignments a student can see: their class, or set for every class."""
    return "archived = 0 AND (grade IS NULL OR grade = ?)" if user["grade"] else "archived = 0"


def _status(conn, assignment_id: int, user_id: int, kind: str) -> dict:
    if kind == "reading":
        done = conn.execute("SELECT completed_at FROM assignment_done WHERE assignment_id = ? AND user_id = ?",
                            (assignment_id, user_id)).fetchone()
        return {"state": "done" if done else "todo", "completed_at": done["completed_at"] if done else None}
    rows = conn.execute(
        """SELECT id, score, total, completed_at FROM quizzes WHERE assignment_id = ? AND user_id = ?
           ORDER BY completed_at IS NULL, score * 1.0 / total DESC""",
        (assignment_id, user_id),
    ).fetchall()
    finished = [r for r in rows if r["completed_at"]]
    if finished:
        best = finished[0]
        return {"state": "done", "completed_at": min(r["completed_at"] for r in finished), "quiz_id": best["id"],
                "score": best["score"], "total": best["total"], "attempts": len(finished)}
    if rows:
        return {"state": "started", "quiz_id": rows[0]["id"]}
    return {"state": "todo"}


# --------------------------------------------------------------------------- students

@student_bp.get("")
def my_assignments():
    user = current_user()
    if user is None or user["is_guest"]:
        return {"assignments": []}
    db = get_db()
    params = (user["grade"],) if user["grade"] else ()
    rows = db.execute(f"SELECT * FROM assignments WHERE {_for_student(user)} ORDER BY due_date IS NULL, due_date, id DESC",
                      params).fetchall()
    out = []
    for row in rows:
        item = _public(db, row)
        item["status"] = _status(db, row["id"], user["id"], row["kind"])
        item["overdue"] = bool(row["due_date"] and row["due_date"] < today() and item["status"]["state"] != "done")
        out.append(item)
    return {"assignments": out}


def _visible(db, user, assignment_id: int):
    if user is None or user["is_guest"]:
        return None
    params = (assignment_id, user["grade"]) if user["grade"] else (assignment_id,)
    return db.execute(f"SELECT * FROM assignments WHERE id = ? AND {_for_student(user)}", params).fetchone()


@student_bp.post("/<int:assignment_id>/start")
def start_assignment(assignment_id: int):
    """Start (or resume) the assessment for an assignment."""
    user = current_user()
    db = get_db()
    row = _visible(db, user, assignment_id)
    if row is None or row["kind"] != "quiz":
        return error("Assignment not found", 404)
    open_quiz = db.execute(
        """SELECT id FROM quizzes WHERE assignment_id = ? AND user_id = ? AND completed_at IS NULL
           AND (answers_json IS NULL OR answers_json = '{}') ORDER BY id DESC""",
        (assignment_id, user["id"]),
    ).fetchone()
    if open_quiz is not None:
        return {"quiz": _quizmaster().detail(db, user, open_quiz["id"])}
    questions = [_shuffle_options(q) for q in json.loads(row["questions_json"] or "[]")]
    if not questions:
        return error("This assignment has no questions")
    random.shuffle(questions)
    slugs = json.loads(row["subjects_json"])
    docs = [d for d in (knowledge.get_document(db, s) for s in slugs) if d]
    made = {"docs": docs, "slugs": slugs, "topic": row["title"], "difficulty": row["difficulty"],
            "questions": questions, "engine": row["engine"] or "library"}
    quiz = _quizmaster().save(db, user, made, row["language"], row["mode"], assignment_id=assignment_id)
    return {"quiz": quiz}, 201


@student_bp.post("/<int:assignment_id>/done")
def mark_reading_done(assignment_id: int):
    user = current_user()
    db = get_db()
    row = _visible(db, user, assignment_id)
    if row is None or row["kind"] != "reading":
        return error("Assignment not found", 404)
    done = (request.get_json(silent=True) or {}).get("done", True)
    if done:
        db.execute("INSERT OR IGNORE INTO assignment_done (assignment_id, user_id, completed_at) VALUES (?, ?, ?)",
                   (assignment_id, user["id"], now_iso()))
    else:
        db.execute("DELETE FROM assignment_done WHERE assignment_id = ? AND user_id = ?", (assignment_id, user["id"]))
    db.commit()
    return {"status": _status(db, assignment_id, user["id"], "reading")}


# --------------------------------------------------------------------------- teachers

def _class_students(db, grade):
    query = "SELECT id, name, grade FROM users WHERE is_guest = 0 AND role = 'student'"
    if grade:
        query += " AND grade = ?"
        return db.execute(query + " ORDER BY name", (grade,)).fetchall()
    return db.execute(query + " ORDER BY name").fetchall()


@teacher_bp.get("")
@require_role("teacher")
def list_assignments():
    db = get_db()
    rows = db.execute("SELECT * FROM assignments ORDER BY archived, created_at DESC").fetchall()
    out = []
    for row in rows:
        item = _public(db, row)
        students = _class_students(db, row["grade"])
        states = [_status(db, row["id"], s["id"], row["kind"]) for s in students]
        scored = [s for s in states if s.get("total")]
        item.update(
            students=len(students),
            done=sum(1 for s in states if s["state"] == "done"),
            started=sum(1 for s in states if s["state"] == "started"),
            average=round(sum(100 * s["score"] / s["total"] for s in scored) / len(scored)) if scored else None,
        )
        out.append(item)
    return {"assignments": out}


@teacher_bp.post("")
@require_role("teacher")
def create_assignment():
    data = request.get_json(silent=True) or {}
    db = get_db()
    title = str(data.get("title", "")).strip()[:120]
    if not title:
        return error("Give the assignment a title")
    kind = data.get("kind")
    if kind not in ("quiz", "reading"):
        return error("Choose an assessment or a reading assignment")
    subjects = [str(s) for s in data.get("subjects") or []][:8]
    if not subjects or any((knowledge.get_document(db, s) or {}).get("kind") != "subject" for s in subjects):
        return error("Choose at least one subject")
    grade = data.get("grade")
    if grade not in (None, "") and (not isinstance(grade, int) or not 1 <= grade <= 12):
        return error("Class must be between 1 and 12")
    due = data.get("due_date") or None
    if due and not _DATE.match(str(due)):
        return error("Due dates look like 2026-10-31")
    mode = data.get("mode") if data.get("mode") in MODES else "practice"
    difficulty = str(data.get("difficulty") or "medium")
    language = languages.normalize(data.get("language"))
    topic = str(data.get("topic") or "").strip()[:80] or None

    questions_json, engine = None, None
    if kind == "quiz":
        count = data.get("count") if isinstance(data.get("count"), int) else 10
        try:
            made = _quizmaster().generate(db, subjects, topic or "", count, difficulty, language)
        except QuizError as exc:
            return error(str(exc))
        questions_json, engine, difficulty = json.dumps(made["questions"], ensure_ascii=False), made["engine"], made["difficulty"]

    user = current_user()
    cur = db.execute(
        """INSERT INTO assignments (teacher_id, title, instructions, kind, subjects_json, topic, grade, mode, difficulty,
                                    language, questions_json, engine, due_date, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (user["id"], title, str(data.get("instructions") or "").strip()[:2000] or None, kind, json.dumps(subjects), topic,
         grade or None, mode, difficulty, language, questions_json, engine, due, now_iso()),
    )
    db.commit()
    return {"assignment": _public(db, db.execute("SELECT * FROM assignments WHERE id = ?", (cur.lastrowid,)).fetchone())}, 201


@teacher_bp.get("/<int:assignment_id>")
@require_role("teacher")
def assignment_progress(assignment_id: int):
    db = get_db()
    row = db.execute("SELECT * FROM assignments WHERE id = ?", (assignment_id,)).fetchone()
    if row is None:
        return error("Assignment not found", 404)
    students = [{"id": s["id"], "name": s["name"], "grade": s["grade"], **_status(db, row["id"], s["id"], row["kind"])}
                for s in _class_students(db, row["grade"])]
    item = _public(db, row)
    item["preview"] = [{"question": q["question"], "options": q["options"], "answer_index": q["answer_index"]}
                       for q in json.loads(row["questions_json"] or "[]")]
    return {"assignment": item, "students": students}


@teacher_bp.patch("/<int:assignment_id>")
@require_role("teacher")
def update_assignment(assignment_id: int):
    db = get_db()
    data = request.get_json(silent=True) or {}
    if db.execute("SELECT 1 FROM assignments WHERE id = ?", (assignment_id,)).fetchone() is None:
        return error("Assignment not found", 404)
    if "archived" in data:
        db.execute("UPDATE assignments SET archived = ? WHERE id = ?", (1 if data["archived"] else 0, assignment_id))
    if "due_date" in data:
        due = data["due_date"] or None
        if due and not _DATE.match(str(due)):
            return error("Due dates look like 2026-10-31")
        db.execute("UPDATE assignments SET due_date = ? WHERE id = ?", (due, assignment_id))
    db.commit()
    return {"assignment": _public(db, db.execute("SELECT * FROM assignments WHERE id = ?", (assignment_id,)).fetchone())}


@teacher_bp.delete("/<int:assignment_id>")
@require_role("teacher")
def delete_assignment(assignment_id: int):
    db = get_db()
    db.execute("UPDATE quizzes SET assignment_id = NULL WHERE assignment_id = ?", (assignment_id,))
    cur = db.execute("DELETE FROM assignments WHERE id = ?", (assignment_id,))
    db.commit()
    if not cur.rowcount:
        return error("Assignment not found", 404)
    return {"ok": True}
