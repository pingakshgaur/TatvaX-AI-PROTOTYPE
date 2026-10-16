"""Progress reports for students, parents and teachers: one learner's level, activity, results per
subject, recent assessments, review deck and assignments, gathered for a printable report."""

import json
from datetime import date, timedelta

from flask import Blueprint

from . import gamification, knowledge, review
from .db import get_db, today
from .security import error, require_role
from .users import current_user

bp = Blueprint("reports", __name__, url_prefix="/api")


def student_report(conn, user_id: int) -> dict:
    user = conn.execute("SELECT id, name, grade, is_guest, created_at FROM users WHERE id = ?", (user_id,)).fetchone()
    progress = gamification.progress(conn, user_id)

    subjects = []
    for doc in knowledge.list_documents(conn, "subject"):
        slug = doc["slug"]
        questions = conn.execute("SELECT COUNT(*) FROM question_log WHERE user_id = ? AND subject = ?", (user_id, slug)).fetchone()[0]
        scores = [100 * r["score"] / r["total"] for r in conn.execute(
            """SELECT score, total FROM quizzes WHERE user_id = ? AND completed_at IS NOT NULL AND total > 0
               AND (subject = ? OR subjects_json LIKE ?)""",
            (user_id, slug, f'%"{slug}"%'),
        )]
        cards = conn.execute("SELECT COUNT(*) FROM review_cards WHERE user_id = ? AND subject = ? AND box < ?",
                             (user_id, slug, review.MASTERED)).fetchone()[0]
        subjects.append({
            "slug": slug, "title": doc["title"], "color": doc["color"], "questions": questions,
            "assessments": len(scores), "average": round(sum(scores) / len(scores)) if scores else None,
            "best": round(max(scores)) if scores else None, "to_review": cards,
        })

    start = (date.fromisoformat(today()) - timedelta(days=29)).isoformat()
    by_day = {r["day"]: r for r in conn.execute(
        "SELECT day, questions, quizzes FROM activity WHERE user_id = ? AND day >= ?", (user_id, start))}
    activity = []
    for offset in range(29, -1, -1):
        day = (date.fromisoformat(today()) - timedelta(days=offset)).isoformat()
        row = by_day.get(day)
        activity.append({"day": day, "questions": row["questions"] if row else 0, "quizzes": row["quizzes"] if row else 0})

    finished = conn.execute(
        "SELECT COUNT(*), AVG(100.0 * score / total), SUM(total), SUM(score) FROM quizzes WHERE user_id = ? AND completed_at IS NOT NULL AND total > 0",
        (user_id,),
    ).fetchone()
    todos = conn.execute("SELECT COUNT(*), SUM(done) FROM todos WHERE user_id = ?", (user_id,)).fetchone()
    assigned = done = 0
    if user and not user["is_guest"]:
        grade = user["grade"]
        rows = conn.execute(
            "SELECT id, kind FROM assignments WHERE archived = 0" + (" AND (grade IS NULL OR grade = ?)" if grade else ""),
            (grade,) if grade else (),
        ).fetchall()
        assigned = len(rows)
        for row in rows:
            if row["kind"] == "reading":
                done += conn.execute("SELECT 1 FROM assignment_done WHERE assignment_id = ? AND user_id = ?",
                                     (row["id"], user_id)).fetchone() is not None
            else:
                done += conn.execute("SELECT 1 FROM quizzes WHERE assignment_id = ? AND user_id = ? AND completed_at IS NOT NULL",
                                     (row["id"], user_id)).fetchone() is not None

    rated = [s for s in subjects if s["average"] is not None]
    rated.sort(key=lambda s: s["average"])
    return {
        "student": {"id": user["id"], "name": user["name"] if not user["is_guest"] else "Guest learner",
                    "grade": user["grade"], "joined": user["created_at"]},
        "generated": today(),
        "level": progress["level"], "xp": progress["xp"], "streak": progress["streak"],
        "badges": [b for b in progress["badges"] if b["earned"]], "badges_total": len(progress["badges"]),
        "totals": {
            "questions": sum(s["questions"] for s in subjects),
            "assessments": finished[0], "average": round(finished[1]) if finished[1] is not None else None,
            "answered": finished[2] or 0, "correct": finished[3] or 0,
            "active_days": sum(1 for d in activity if d["questions"] or d["quizzes"]),
            "todos": todos[0], "todos_done": todos[1] or 0, "assigned": assigned, "assigned_done": done,
        },
        "subjects": subjects,
        "strongest": rated[-1]["title"] if len(rated) > 1 else None,
        "needs_work": rated[0]["title"] if len(rated) > 1 and rated[0]["average"] < 70 else None,
        "activity": activity,
        "recent": _recent(conn, user_id),
        "review": review.summary(conn, user_id),
    }


def _recent(conn, user_id: int) -> list[dict]:
    titles = {r["slug"]: r["title"] for r in conn.execute("SELECT slug, title FROM documents")}
    out = []
    for r in conn.execute(
        """SELECT id, subject, subjects_json, topic, score, total, mode, completed_at FROM quizzes
           WHERE user_id = ? AND completed_at IS NOT NULL ORDER BY completed_at DESC LIMIT 12""",
        (user_id,),
    ):
        slugs = json.loads(r["subjects_json"]) if r["subjects_json"] else [r["subject"]]
        out.append({"id": r["id"], "subject": " + ".join(titles.get(s, s) for s in slugs), "topic": r["topic"],
                    "score": r["score"], "total": r["total"], "mode": r["mode"], "completed_at": r["completed_at"]})
    return out


@bp.get("/report")
def my_report():
    user = current_user()
    if user is None:
        return error("Ask a question or take an assessment first, then your report will be ready.", 404)
    return {"report": student_report(get_db(), user["id"])}


@bp.get("/admin/students/<int:student_id>/report")
@require_role("teacher")
def student_report_for_teacher(student_id: int):
    db = get_db()
    if db.execute("SELECT 1 FROM users WHERE id = ? AND is_guest = 0", (student_id,)).fetchone() is None:
        return error("Student not found", 404)
    return {"report": student_report(db, student_id)}
