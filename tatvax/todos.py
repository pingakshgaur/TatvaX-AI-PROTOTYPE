"""A personal to-do list for every learner: tasks with notes, priority, due date, subject,
tags and sub-tasks, which can be reordered, duplicated and managed in bulk."""

import json
import re

from flask import Blueprint, request

from . import knowledge
from .db import get_db, now_iso, today
from .security import error
from .users import current_user

bp = Blueprint("todos", __name__, url_prefix="/api/todos")

PRIORITIES = ("low", "medium", "high", "urgent")
MAX_TODOS = 500
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _public(row) -> dict:
    item = dict(row)
    item["done"] = bool(item["done"])
    item["tags"] = json.loads(item["tags"]) if item["tags"] else []
    item["subtasks"] = json.loads(item["subtasks"]) if item["subtasks"] else []
    item.pop("user_id", None)
    return item


def _clean(data: dict, conn, partial: bool) -> tuple[dict, str | None]:
    out: dict = {}
    if "title" in data or not partial:
        title = str(data.get("title", "")).strip()
        if not title:
            return {}, "Give the task a title"
        out["title"] = title[:200]
    if "notes" in data:
        out["notes"] = str(data["notes"] or "").strip()[:4000] or None
    if "priority" in data:
        if data["priority"] not in PRIORITIES:
            return {}, "Priority must be low, medium, high or urgent"
        out["priority"] = data["priority"]
    if "due_date" in data:
        due = data["due_date"] or None
        if due and not _DATE.match(str(due)):
            return {}, "Due dates look like 2026-10-31"
        out["due_date"] = due
    if "subject" in data:
        subject = data["subject"] or None
        if subject and knowledge.get_document(conn, subject) is None:
            return {}, "Unknown subject"
        out["subject"] = subject
    if "tags" in data:
        tags = data["tags"] or []
        if not isinstance(tags, list) or len(tags) > 8:
            return {}, "Use up to 8 tags"
        out["tags"] = json.dumps(list(dict.fromkeys(str(t).strip()[:24] for t in tags if str(t).strip())), ensure_ascii=False)
    if "subtasks" in data:
        subtasks = data["subtasks"] or []
        if not isinstance(subtasks, list) or len(subtasks) > 30:
            return {}, "Use up to 30 sub-tasks"
        out["subtasks"] = json.dumps([{"text": str(s.get("text", "")).strip()[:200], "done": bool(s.get("done"))}
                                      for s in subtasks if isinstance(s, dict) and str(s.get("text", "")).strip()],
                                     ensure_ascii=False)
    if "link" in data:
        link = str(data["link"] or "").strip()[:300] or None
        # Only pages inside TatvaX, never another site.
        if link and (not link.startswith("/") or link.startswith("//") or "\\" in link):
            return {}, "Links must point to a page in TatvaX"
        out["link"] = link
    if "done" in data:
        out["done"] = 1 if data["done"] else 0
        out["completed_at"] = now_iso() if data["done"] else None
    if "position" in data:
        if not isinstance(data["position"], int):
            return {}, "Position must be a number"
        out["position"] = data["position"]
    return out, None


def _own(conn, user, todo_id: int):
    return conn.execute("SELECT * FROM todos WHERE id = ? AND user_id = ?", (todo_id, user["id"])).fetchone()


@bp.get("")
def list_todos():
    user = current_user()
    if user is None:
        return {"todos": []}
    rows = get_db().execute(
        "SELECT * FROM todos WHERE user_id = ? ORDER BY done, position, id DESC", (user["id"],)
    ).fetchall()
    return {"todos": [_public(r) for r in rows]}


@bp.get("/summary")
def todo_summary():
    """What needs attention: open tasks due today or already overdue (for reminders)."""
    user = current_user()
    if user is None:
        return {"today": 0, "overdue": 0, "open": 0, "next": []}
    db = get_db()
    day = today()
    rows = db.execute(
        """SELECT * FROM todos WHERE user_id = ? AND done = 0 AND due_date IS NOT NULL AND due_date <= ?
           ORDER BY due_date, position LIMIT 5""",
        (user["id"], day),
    ).fetchall()
    counts = db.execute(
        """SELECT COUNT(*), SUM(due_date = ?), SUM(due_date < ?) FROM todos WHERE user_id = ? AND done = 0""",
        (day, day, user["id"]),
    ).fetchone()
    return {"open": counts[0], "today": counts[1] or 0, "overdue": counts[2] or 0, "next": [_public(r) for r in rows]}


@bp.post("")
def create_todo():
    user = current_user(create=True)
    db = get_db()
    if db.execute("SELECT COUNT(*) FROM todos WHERE user_id = ?", (user["id"],)).fetchone()[0] >= MAX_TODOS:
        return error(f"You can keep up to {MAX_TODOS} tasks. Clear some completed ones first.")
    data, problem = _clean(request.get_json(silent=True) or {}, db, partial=False)
    if problem:
        return error(problem)
    top = db.execute("SELECT COALESCE(MIN(position), 0) FROM todos WHERE user_id = ?", (user["id"],)).fetchone()[0]
    data.setdefault("position", top - 1)  # new tasks go to the top
    data.setdefault("priority", "medium")
    columns = ["user_id", *data.keys(), "created_at", "updated_at"]
    cur = db.execute(
        f"INSERT INTO todos ({', '.join(columns)}) VALUES ({', '.join('?' for _ in columns)})",
        (user["id"], *data.values(), now_iso(), now_iso()),
    )
    db.commit()
    return {"todo": _public(_own(db, user, cur.lastrowid))}, 201


@bp.patch("/<int:todo_id>")
def update_todo(todo_id: int):
    user = current_user()
    db = get_db()
    if user is None or _own(db, user, todo_id) is None:
        return error("Task not found", 404)
    data, problem = _clean(request.get_json(silent=True) or {}, db, partial=True)
    if problem:
        return error(problem)
    if data:
        data["updated_at"] = now_iso()
        assignments = ", ".join(f"{column} = ?" for column in data)
        db.execute(f"UPDATE todos SET {assignments} WHERE id = ?", (*data.values(), todo_id))
        db.commit()
    return {"todo": _public(_own(db, user, todo_id))}


@bp.delete("/<int:todo_id>")
def delete_todo(todo_id: int):
    user = current_user()
    db = get_db()
    if user is None or _own(db, user, todo_id) is None:
        return error("Task not found", 404)
    db.execute("DELETE FROM todos WHERE id = ?", (todo_id,))
    db.commit()
    return {"ok": True}


@bp.post("/<int:todo_id>/duplicate")
def duplicate_todo(todo_id: int):
    user = current_user()
    db = get_db()
    row = _own(db, user, todo_id) if user else None
    if row is None:
        return error("Task not found", 404)
    cur = db.execute(
        """INSERT INTO todos (user_id, title, notes, priority, due_date, subject, tags, subtasks, link, position,
                              created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (user["id"], f"{row['title']} (copy)"[:200], row["notes"], row["priority"], row["due_date"], row["subject"],
         row["tags"], row["subtasks"], row["link"], row["position"], now_iso(), now_iso()),
    )
    db.commit()
    return {"todo": _public(_own(db, user, cur.lastrowid))}, 201


@bp.post("/reorder")
def reorder_todos():
    user = current_user()
    ids = (request.get_json(silent=True) or {}).get("ids")
    if user is None or not isinstance(ids, list) or not all(isinstance(i, int) for i in ids):
        return error("Send the task ids in their new order")
    db = get_db()
    for position, todo_id in enumerate(ids):
        db.execute("UPDATE todos SET position = ? WHERE id = ? AND user_id = ?", (position, todo_id, user["id"]))
    db.commit()
    return {"ok": True}


@bp.post("/bulk")
def bulk_todos():
    """Act on several tasks at once: complete, reopen or delete; "clear_completed" needs no ids."""
    user = current_user()
    data = request.get_json(silent=True) or {}
    action, ids = data.get("action"), data.get("ids") or []
    if user is None:
        return {"changed": 0}
    if action not in ("complete", "reopen", "delete", "clear_completed"):
        return error("Unknown action")
    if action != "clear_completed" and (not isinstance(ids, list) or not all(isinstance(i, int) for i in ids)):
        return error("Send the task ids to change")
    db = get_db()
    marks = ", ".join("?" for _ in ids) or "NULL"
    if action == "complete":
        cur = db.execute(f"UPDATE todos SET done = 1, completed_at = ?, updated_at = ? WHERE user_id = ? AND id IN ({marks})",
                         (now_iso(), now_iso(), user["id"], *ids))
    elif action == "reopen":
        cur = db.execute(f"UPDATE todos SET done = 0, completed_at = NULL, updated_at = ? WHERE user_id = ? AND id IN ({marks})",
                         (now_iso(), user["id"], *ids))
    elif action == "delete":
        cur = db.execute(f"DELETE FROM todos WHERE user_id = ? AND id IN ({marks})", (user["id"], *ids))
    else:
        cur = db.execute("DELETE FROM todos WHERE user_id = ? AND done = 1", (user["id"],))
    db.commit()
    return {"changed": cur.rowcount}
