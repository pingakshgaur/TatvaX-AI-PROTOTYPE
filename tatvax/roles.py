"""Roles and permissions, ranked like a Discord server.

Every role has a position: a higher role outranks every role below it. The Owner role is always at
the top and has every permission; the base role ("Student") is always at the bottom and everyone has
it, guests included. Other roles sit in between, and each has its own set of permissions.

The rules that keep the ranking meaningful:
- you can only create, edit, move, delete or hand out roles that are below your own highest role;
- you can't give a role a permission you don't have yourself;
- you can't change the roles of someone whose highest role is level with or above yours;
- only the Owner can pass ownership to someone else.
"""

import json
from functools import wraps

from flask import Blueprint, request
from werkzeug.security import check_password_hash

from .db import get_db, now_iso
from .security import error

bp = Blueprint("roles", __name__, url_prefix="/api/admin")

# id: (name, description, group)
PERMISSIONS = {
    "administrator": ("Administrator", "Every permission, including any added later. Only for people you trust completely.", "Management"),
    "manage_roles": ("Manage roles", "Create, edit and arrange the roles below their own, and give them to people ranked below them.", "Management"),
    "manage_ai": ("Manage AI settings", "Choose the AI provider and model, and save or reveal API keys.", "Management"),
    "manage_content": ("Manage study notes", "Create, edit and delete subjects and the school information TatvAI answers from.", "Teaching"),
    "manage_assignments": ("Manage assignments", "Set assessments and reading for classes and see how everyone is doing.", "Teaching"),
    "view_students": ("View students", "See the students table and download any student's progress report.", "Teaching"),
    "view_analytics": ("View class analytics", "See the overview of questions, languages and assessment scores.", "Teaching"),
    "view_feedback": ("Read feedback", "Read the feedback people send from the app.", "Teaching"),
    "ask_tutor": ("Ask the tutor", "Ask questions in the subject tutor and TatvAI.", "Learning"),
    "photo_questions": ("Ask with a photo", "Attach a photo to a question (needs an AI provider that reads pictures).", "Learning"),
    "take_assessments": ("Take assessments", "Start assessments, retakes and assignment assessments.", "Learning"),
    "use_translator": ("Use the translator", "Translate text and answers between languages.", "Learning"),
}
ALL = frozenset(PERMISSIONS)
LEARNING = frozenset(p for p, (_n, _d, group) in PERMISSIONS.items() if group == "Learning")
STAFF = ALL - LEARNING  # holding any of these opens the teacher console

OWNER_POSITION = 1_000_000  # always the top
BASE_POSITION = 0           # always the bottom

DEFAULT_ROLES = [
    # key, name, colour, position, permissions
    ("owner", "Owner", "#b45309", OWNER_POSITION, sorted(ALL)),
    ("admin", "Admin", "#be123c", 3, ["administrator"]),
    ("teacher", "Teacher", "#0f766e", 2, ["manage_content", "manage_assignments", "view_students", "view_analytics",
                                          "view_feedback", *sorted(LEARNING)]),
    ("student", "Student", "#64748b", BASE_POSITION, sorted(LEARNING)),
]


# --------------------------------------------------------------------------- setup

def ensure_defaults(conn) -> None:
    """Create the default roles once. On an install that had teachers before roles existed, the
    first teacher becomes the Owner and the others become Admins, so nobody loses access."""
    if conn.execute("SELECT COUNT(*) FROM roles").fetchone()[0]:
        return
    for key, name, color, position, permissions in DEFAULT_ROLES:
        conn.execute("INSERT INTO roles (key, name, color, position, permissions, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                     (key, name, color, position, json.dumps(permissions), now_iso()))
    teachers = [r["id"] for r in conn.execute(
        "SELECT id FROM users WHERE role = 'teacher' AND is_guest = 0 ORDER BY id")]
    if teachers:
        assign(conn, teachers[0], role_id(conn, "owner"))
        for uid in teachers[1:]:
            assign(conn, uid, role_id(conn, "admin"))
    conn.commit()


def role_id(conn, key: str) -> int | None:
    row = conn.execute("SELECT id FROM roles WHERE key = ?", (key,)).fetchone()
    return row["id"] if row else None


def assign(conn, user_id: int, rid: int | None, by: int | None = None) -> None:
    if rid is None:
        return
    conn.execute("INSERT OR IGNORE INTO user_roles (user_id, role_id, assigned_at, assigned_by) VALUES (?, ?, ?, ?)",
                 (user_id, rid, now_iso(), by))
    refresh_cache(conn, [user_id])


# --------------------------------------------------------------------------- who can do what

def _perms(row) -> set[str]:
    try:
        return set(json.loads(row["permissions"])) & ALL
    except (TypeError, ValueError):
        return set()


def held_roles(conn, user_id: int | None) -> list:
    """The roles a user holds, highest first, including the base role everyone has."""
    rows = conn.execute(
        """SELECT * FROM roles WHERE key = 'student'
           OR id IN (SELECT role_id FROM user_roles WHERE user_id = ?) ORDER BY position DESC""",
        (user_id or -1,),
    ).fetchall()
    return rows


def access(conn, user) -> dict:
    """{permissions, rank, roles, is_owner} for a user (or for a visitor with no profile yet)."""
    roles = held_roles(conn, user["id"] if user else None)
    if user is not None and user["is_guest"]:
        roles = [r for r in roles if r["key"] == "student"]  # guests only ever have the base role
    perms: set[str] = set()
    for r in roles:
        perms |= _perms(r)
    is_owner = any(r["key"] == "owner" for r in roles)
    if is_owner or "administrator" in perms:
        perms = set(ALL)
    return {
        "permissions": perms,
        "rank": max((r["position"] for r in roles), default=BASE_POSITION),
        "roles": roles,
        "is_owner": is_owner,
    }


def can(conn, user, permission: str) -> bool:
    return permission in access(conn, user)["permissions"]


def refresh_cache(conn, user_ids: list[int] | None = None) -> None:
    """users.role is kept as a quick "teacher" (staff) / "student" marker for class lists, the
    students table and the leaderboard. Someone with staff permissions counts as staff, unless
    they have a class: a student who is also Class Monitor is still a learner in their class."""
    if user_ids is None:
        user_ids = [r["id"] for r in conn.execute("SELECT id FROM users WHERE is_guest = 0")]
    for uid in user_ids:
        user = conn.execute("SELECT id, is_guest, grade FROM users WHERE id = ?", (uid,)).fetchone()
        if user is None:
            continue
        staff = bool(access(conn, user)["permissions"] & STAFF) and user["grade"] is None
        conn.execute("UPDATE users SET role = ? WHERE id = ?", ("teacher" if staff else "student", uid))


def public_access(conn, user) -> dict:
    info = access(conn, user)
    top = info["roles"][0] if info["roles"] else None
    return {
        "permissions": sorted(info["permissions"]),
        "staff": bool(info["permissions"] & STAFF),
        "is_owner": info["is_owner"],
        "roles": [{"id": r["id"], "name": r["name"], "color": r["color"]} for r in info["roles"] if r["key"] != "student"],
        "top_role": {"name": top["name"], "color": top["color"]} if top else None,
    }


def require_permission(*permissions):
    """The signed-in user needs at least one of these permissions."""
    def decorator(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            from .users import current_user

            user = current_user()
            if user is None or user["is_guest"]:
                return error("Please sign in first", 401)
            if not access(get_db(), user)["permissions"] & set(permissions):
                return error("Your role doesn't allow this. Ask someone with a higher role.", 403)
            return view(*args, **kwargs)

        return wrapper

    return decorator


def learning_allowed(conn, user, permission: str) -> str | None:
    """For learning features: None if allowed, otherwise the message to show."""
    if can(conn, user, permission):
        return None
    name = PERMISSIONS[permission][0].lower()
    return f"Your role doesn't include “{name}”. Ask your teacher if you need it."


# --------------------------------------------------------------------------- API

def _me():
    from .users import current_user

    return current_user()


def _role_out(conn, row, me: dict, members: dict) -> dict:
    system = row["key"] in ("owner", "student")
    below_me = me["is_owner"] or row["position"] < me["rank"]
    return {
        "id": row["id"], "key": row["key"], "name": row["name"], "color": row["color"], "position": row["position"],
        "permissions": sorted(_perms(row)),
        "members": members.get(row["id"], 0) if row["key"] != "student" else None,
        "base": row["key"] == "student", "owner": row["key"] == "owner",
        # What the person looking may do with this role.
        "editable": below_me and row["key"] != "owner",
        "deletable": below_me and not system,
        "movable": below_me and not system,
        "assignable": below_me and not system,
    }


def _listing(conn):
    me = access(conn, _me())
    members = {r["role_id"]: r["n"] for r in conn.execute("SELECT role_id, COUNT(*) AS n FROM user_roles GROUP BY role_id")}
    rows = conn.execute("SELECT * FROM roles ORDER BY position DESC").fetchall()
    return {
        "roles": [_role_out(conn, r, me, members) for r in rows],
        "permissions": [{"id": p, "name": n, "description": d, "group": g} for p, (n, d, g) in PERMISSIONS.items()],
        "me": {"rank": me["rank"], "is_owner": me["is_owner"], "permissions": sorted(me["permissions"])},
    }


def _clean_role(data: dict, me: dict, current: set[str] | None) -> tuple[dict, str | None]:
    import re

    out: dict = {}
    if "name" in data or current is None:
        name = " ".join(str(data.get("name", "")).split())[:40]
        if not name:
            return {}, "Give the role a name"
        out["name"] = name
    if "color" in data:
        color = str(data["color"])
        if not re.match(r"^#[0-9a-fA-F]{6}$", color):
            return {}, "Colours look like #0f766e"
        out["color"] = color
    if "permissions" in data:
        wanted = data["permissions"]
        if not isinstance(wanted, list) or any(p not in ALL for p in wanted):
            return {}, "Unknown permission"
        wanted = set(wanted)
        # You can't hand out a power you don't have, nor take away one you don't have.
        changed = wanted ^ (current or set())
        missing = changed - me["permissions"]
        if missing:
            return {}, f"You can't give or remove permissions you don't have yourself: {', '.join(PERMISSIONS[p][0] for p in sorted(missing))}"
        out["permissions"] = json.dumps(sorted(wanted))
    return out, None


def _guard_role(conn, rid: int, me: dict, action: str):
    row = conn.execute("SELECT * FROM roles WHERE id = ?", (rid,)).fetchone()
    if row is None:
        return None, error("Role not found", 404)
    if row["key"] == "owner":
        return None, error("The Owner role always has every permission and can't be changed", 403)
    if not me["is_owner"] and row["position"] >= me["rank"]:
        return None, error(f"You can only {action} roles below your own highest role", 403)
    return row, None


@bp.get("/roles")
@require_permission("manage_roles")
def list_roles():
    return _listing(get_db())


@bp.post("/roles")
@require_permission("manage_roles")
def create_role():
    conn = get_db()
    me = access(conn, _me())
    if conn.execute("SELECT COUNT(*) FROM roles").fetchone()[0] >= 50:
        return error("A school can have up to 50 roles")
    clean, problem = _clean_role(request.get_json(silent=True) or {}, me, None)
    if problem:
        return error(problem)
    # Like Discord, a new role starts at the bottom, just above the base role.
    conn.execute("UPDATE roles SET position = position + 1 WHERE position > ? AND position < ?", (BASE_POSITION, OWNER_POSITION))
    conn.execute("INSERT INTO roles (name, color, position, permissions, created_at) VALUES (?, ?, ?, ?, ?)",
                 (clean["name"], clean.get("color", "#6366f1"), BASE_POSITION + 1, clean.get("permissions", "[]"), now_iso()))
    conn.commit()
    return _listing(conn), 201


@bp.patch("/roles/<int:rid>")
@require_permission("manage_roles")
def update_role(rid: int):
    conn = get_db()
    me = access(conn, _me())
    row, problem = _guard_role(conn, rid, me, "edit")
    if problem:
        return problem
    clean, message = _clean_role(request.get_json(silent=True) or {}, me, _perms(row))
    if message:
        return error(message)
    if clean:
        columns = ", ".join(f"{c} = ?" for c in clean)
        conn.execute(f"UPDATE roles SET {columns} WHERE id = ?", (*clean.values(), rid))
        if "permissions" in clean:
            refresh_cache(conn)
        conn.commit()
    return _listing(conn)


@bp.delete("/roles/<int:rid>")
@require_permission("manage_roles")
def delete_role(rid: int):
    conn = get_db()
    me = access(conn, _me())
    row, problem = _guard_role(conn, rid, me, "delete")
    if problem:
        return problem
    if row["key"] == "student":
        return error("Everyone has the base role, so it can't be deleted", 403)
    holders = [r["user_id"] for r in conn.execute("SELECT user_id FROM user_roles WHERE role_id = ?", (rid,))]
    conn.execute("DELETE FROM roles WHERE id = ?", (rid,))
    conn.execute("UPDATE roles SET position = position - 1 WHERE position > ? AND position < ?", (row["position"], OWNER_POSITION))
    refresh_cache(conn, holders)
    conn.commit()
    return _listing(conn)


@bp.post("/roles/<int:rid>/move")
@require_permission("manage_roles")
def move_role(rid: int):
    """Swap a role with the one just above or below it."""
    conn = get_db()
    me = access(conn, _me())
    row, problem = _guard_role(conn, rid, me, "move")
    if problem:
        return problem
    if row["key"] == "student":
        return error("The base role always stays at the bottom", 403)
    direction = (request.get_json(silent=True) or {}).get("direction")
    if direction not in ("up", "down"):
        return error("Move a role up or down")
    neighbour = conn.execute(
        "SELECT * FROM roles WHERE position > ? AND position < ? ORDER BY position LIMIT 1" if direction == "up"
        else "SELECT * FROM roles WHERE position < ? AND position > ? ORDER BY position DESC LIMIT 1",
        (row["position"], OWNER_POSITION) if direction == "up" else (row["position"], BASE_POSITION),
    ).fetchone()
    if neighbour is None:
        return error("It's already as far as it can go")
    if not me["is_owner"] and neighbour["position"] >= me["rank"]:
        return error("A role can't be moved up to or above your own highest role", 403)
    conn.execute("UPDATE roles SET position = ? WHERE id = ?", (neighbour["position"], row["id"]))
    conn.execute("UPDATE roles SET position = ? WHERE id = ?", (row["position"], neighbour["id"]))
    conn.commit()
    return _listing(conn)


@bp.get("/members")
@require_permission("manage_roles")
def list_members():
    return _members(get_db())


def _members(conn) -> dict:
    me = access(conn, _me())
    me_id = _me()["id"]
    query = (request.args.get("q") or "").strip().lower()
    users = conn.execute(
        "SELECT id, name, email, grade FROM users WHERE is_guest = 0 ORDER BY name LIMIT 1000").fetchall()
    out = []
    for u in users:
        if query and query not in u["name"].lower() and query not in (u["email"] or "").lower():
            continue
        info = access(conn, {"id": u["id"], "is_guest": 0})
        out.append({
            "id": u["id"], "name": u["name"], "email": u["email"], "grade": u["grade"],
            "roles": [r["id"] for r in info["roles"] if r["key"] != "student"],
            "rank": info["rank"], "is_owner": info["is_owner"], "is_me": u["id"] == me_id,
            # Only people ranked below you can have their roles changed by you.
            "manageable": (me["is_owner"] and u["id"] != me_id) or info["rank"] < me["rank"],
        })
    out.sort(key=lambda m: (-m["rank"], m["name"].lower()))
    return {"members": out, **_listing(conn)}


@bp.put("/members/<int:uid>/roles")
@require_permission("manage_roles")
def set_member_roles(uid: int):
    conn = get_db()
    actor = _me()
    me = access(conn, actor)
    target = conn.execute("SELECT id, is_guest FROM users WHERE id = ?", (uid,)).fetchone()
    if target is None or target["is_guest"]:
        return error("Person not found", 404)
    theirs = access(conn, target)
    if uid == actor["id"] and not me["is_owner"]:
        return error("You can't change your own roles. Ask someone ranked above you.", 403)
    if not me["is_owner"] and theirs["rank"] >= me["rank"]:
        return error("You can only change the roles of people ranked below you", 403)
    wanted = (request.get_json(silent=True) or {}).get("role_ids")
    if not isinstance(wanted, list) or not all(isinstance(i, int) for i in wanted):
        return error("Send the list of role ids")
    current = {r["id"] for r in theirs["roles"] if r["key"] != "student"}
    wanted = set(wanted)
    for rid in current ^ wanted:  # every role being given or taken away
        row = conn.execute("SELECT * FROM roles WHERE id = ?", (rid,)).fetchone()
        if row is None:
            return error("Role not found", 404)
        if row["key"] in ("owner", "student"):
            return error("Ownership is passed on with “Transfer ownership”, and everyone has the base role", 403)
        if not me["is_owner"] and row["position"] >= me["rank"]:
            return error(f"You can only give or take away roles below your own highest role ({row['name']} isn't)", 403)
    for rid in current - wanted:
        conn.execute("DELETE FROM user_roles WHERE user_id = ? AND role_id = ?", (uid, rid))
    for rid in wanted - current:
        conn.execute("INSERT INTO user_roles (user_id, role_id, assigned_at, assigned_by) VALUES (?, ?, ?, ?)",
                     (uid, rid, now_iso(), actor["id"]))
    refresh_cache(conn, [uid])
    conn.commit()
    return _members(conn)


@bp.post("/owner/transfer")
@require_permission("administrator")
def transfer_ownership():
    """The Owner hands ownership to someone else (and keeps the Admin role, if it still exists)."""
    conn = get_db()
    actor = _me()
    if not access(conn, actor)["is_owner"]:
        return error("Only the Owner can transfer ownership", 403)
    data = request.get_json(silent=True) or {}
    if not check_password_hash(actor["password_hash"] or "", str(data.get("password", ""))):
        return error("That password isn't right", 403)
    target = conn.execute("SELECT id, is_guest FROM users WHERE id = ?", (data.get("user_id"),)).fetchone()
    if target is None or target["is_guest"] or target["id"] == actor["id"]:
        return error("Choose another registered person")
    owner = role_id(conn, "owner")
    conn.execute("DELETE FROM user_roles WHERE role_id = ?", (owner,))
    assign(conn, target["id"], owner, by=actor["id"])
    assign(conn, actor["id"], role_id(conn, "admin"), by=actor["id"])
    refresh_cache(conn, [actor["id"], target["id"]])
    conn.commit()
    return _members(conn)
