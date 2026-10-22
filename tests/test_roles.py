"""Roles ranked like a Discord server: higher roles outrank lower ones, and each role has its own permissions."""

from conftest import ask, register

from tatvax import db as tatvax_db
from tatvax import roles


def roles_by_name(client):
    return {r["name"]: r for r in client.get("/api/admin/roles").get_json()["roles"]}


def member(client, name):
    return next(m for m in client.get("/api/admin/members").get_json()["members"] if m["name"] == name)


def give(owner, person, *role_names):
    ids = [roles_by_name(owner)[n]["id"] for n in role_names]
    response = owner.put(f"/api/admin/members/{member(owner, person)['id']}/roles", json={"role_ids": ids})
    assert response.status_code == 200, response.get_json()


def people(app):
    """An Owner, an Admin, a Teacher and a Student, each signed in on their own client."""
    owner = app.test_client()
    register(owner, name="Owner", email="owner@example.test")
    admin = app.test_client()
    register(admin, name="Admin", email="admin@example.test")
    teacher = app.test_client()
    register(teacher, name="Teacher", email="teacher@example.test", teacher_code="staff-code")
    student = app.test_client()
    register(student, name="Student", email="student@example.test")
    give(owner, "Admin", "Admin")
    return owner, admin, teacher, student


def test_default_ladder(client):
    user = register(client).get_json()["user"]
    assert user["is_owner"] and user["staff"] and user["role"] == "teacher"
    assert set(user["permissions"]) == set(roles.ALL)
    ladder = [r["name"] for r in client.get("/api/admin/roles").get_json()["roles"]]
    assert ladder == ["Owner", "Admin", "Teacher", "Student"]


def test_each_role_only_opens_its_own_tools(app):
    owner, admin, teacher, student = people(app)
    assert teacher.get("/api/admin/documents/science").status_code == 200        # manage_content
    assert teacher.get("/api/admin/overview").status_code == 200                 # view_analytics
    assert teacher.get("/api/admin/ai").status_code == 403                       # no manage_ai
    assert teacher.get("/api/admin/roles").status_code == 403                    # no manage_roles
    assert admin.get("/api/admin/ai").status_code == 200                         # administrator: everything
    assert student.get("/api/admin/overview").status_code == 403
    assert student.get("/api/me").get_json()["user"]["staff"] is False


def test_a_new_role_starts_at_the_bottom_and_grants_its_permissions(app):
    owner, admin, teacher, student = people(app)
    created = owner.post("/api/admin/roles", json={"name": "Class monitor", "color": "#7c3aed",
                                                   "permissions": ["view_analytics"]})
    assert created.status_code == 201
    ladder = [r["name"] for r in created.get_json()["roles"]]
    assert ladder == ["Owner", "Admin", "Teacher", "Class monitor", "Student"]
    give(owner, "Student", "Class monitor")
    me = student.get("/api/me").get_json()["user"]
    assert me["staff"] and me["top_role"]["name"] == "Class monitor"
    assert student.get("/api/admin/overview").status_code == 200
    assert student.get("/api/admin/students").status_code == 403


def test_nobody_can_touch_roles_at_or_above_their_own(app):
    owner, admin, teacher, student = people(app)
    r = roles_by_name(owner)
    assert admin.patch(f"/api/admin/roles/{r['Admin']['id']}", json={"name": "Boss"}).status_code == 403
    assert admin.patch(f"/api/admin/roles/{r['Owner']['id']}", json={"name": "Me"}).status_code == 403
    assert admin.delete(f"/api/admin/roles/{r['Admin']['id']}").status_code == 403
    assert admin.patch(f"/api/admin/roles/{r['Teacher']['id']}", json={"name": "Class teacher"}).status_code == 200
    # Can't move a role up to (or past) your own.
    assert admin.post(f"/api/admin/roles/{r['Teacher']['id']}/move", json={"direction": "up"}).status_code == 403
    # Can't give out a role at your own level, or change someone ranked level with or above you.
    response = admin.put(f"/api/admin/members/{member(admin, 'Student')['id']}/roles", json={"role_ids": [r["Admin"]["id"]]})
    assert response.status_code == 403
    assert admin.put(f"/api/admin/members/{member(admin, 'Owner')['id']}/roles", json={"role_ids": []}).status_code == 403
    assert admin.put(f"/api/admin/members/{member(admin, 'Admin')['id']}/roles", json={"role_ids": []}).status_code == 403
    # But people ranked below are fine.
    give(admin, "Student", "Class teacher")
    assert member(admin, "Student")["manageable"] and not member(admin, "Owner")["manageable"]


def test_permissions_you_do_not_have_cannot_be_given(app):
    owner, admin, teacher, student = people(app)
    owner.post("/api/admin/roles", json={"name": "Coordinator", "permissions": ["manage_roles", "view_analytics"]})
    r = roles_by_name(owner)
    owner.post(f"/api/admin/roles/{r['Coordinator']['id']}/move", json={"direction": "up"})  # above Teacher
    give(owner, "Teacher", "Coordinator")
    response = teacher.post("/api/admin/roles", json={"name": "Sneaky", "permissions": ["manage_ai"]})
    assert response.status_code == 400 and "don't have" in response.get_json()["error"]
    assert teacher.post("/api/admin/roles", json={"name": "Helper", "permissions": ["view_analytics"]}).status_code == 201


def test_moving_and_deleting_roles(app):
    owner, admin, teacher, student = people(app)
    owner.post("/api/admin/roles", json={"name": "Helper", "permissions": ["view_feedback"]})
    r = roles_by_name(owner)
    ladder = owner.post(f"/api/admin/roles/{r['Helper']['id']}/move", json={"direction": "up"}).get_json()["roles"]
    assert [x["name"] for x in ladder] == ["Owner", "Admin", "Helper", "Teacher", "Student"]
    assert owner.post(f"/api/admin/roles/{r['Student']['id']}/move", json={"direction": "up"}).status_code == 403
    assert owner.delete(f"/api/admin/roles/{r['Student']['id']}").status_code == 403
    assert owner.delete(f"/api/admin/roles/{r['Owner']['id']}").status_code == 403

    give(owner, "Student", "Helper")
    assert student.get("/api/admin/feedback").status_code == 200
    owner.delete(f"/api/admin/roles/{r['Helper']['id']}")
    assert student.get("/api/admin/feedback").status_code == 403
    assert student.get("/api/me").get_json()["user"]["role"] == "student"


def test_the_base_role_controls_what_learners_can_do(app):
    owner, admin, teacher, student = people(app)
    base = roles_by_name(owner)["Student"]
    keep = [p for p in base["permissions"] if p not in ("ask_tutor", "take_assessments")]
    assert owner.patch(f"/api/admin/roles/{base['id']}", json={"permissions": keep}).status_code == 200
    blocked = student.post("/api/chat", json={"message": "What is a fraction?", "mode": "subject", "subject": "mathematics"})
    assert blocked.status_code == 403 and "ask the tutor" in blocked.get_json()["error"]
    assert student.post("/api/quiz", json={"subjects": ["science"], "count": 3}).status_code == 403
    assert app.test_client().post("/api/quiz", json={"subjects": ["science"], "count": 3}).status_code == 403  # guests too
    ask(teacher, "What is a fraction?")  # the Teacher role has its own learning permissions


def test_ownership_can_only_be_passed_on_by_the_owner(app):
    owner, admin, teacher, student = people(app)
    target = member(owner, "Teacher")["id"]
    assert admin.post("/api/admin/owner/transfer", json={"user_id": target, "password": "correct-horse"}).status_code == 403
    assert owner.post("/api/admin/owner/transfer", json={"user_id": target, "password": "wrong"}).status_code == 403
    assert owner.post("/api/admin/owner/transfer", json={"user_id": target, "password": "correct-horse"}).status_code == 200
    assert teacher.get("/api/me").get_json()["user"]["is_owner"]
    former = owner.get("/api/me").get_json()["user"]
    assert not former["is_owner"] and former["top_role"]["name"] == "Admin"


def test_teachers_from_before_roles_keep_their_access(tmp_path):
    path = str(tmp_path / "old.db")
    conn = tatvax_db.connect(path)
    conn.executescript(tatvax_db.SCHEMA)
    tatvax_db.migrate(conn)
    conn.execute("DELETE FROM roles")
    for i, role in enumerate(["teacher", "teacher", "student"]):
        conn.execute("INSERT INTO users (name, email, role, is_guest, created_at) VALUES (?, ?, ?, 0, 'x')",
                     (f"U{i}", f"u{i}@example.test", role))
    conn.commit()
    roles.ensure_defaults(conn)
    first, second, third = (dict(conn.execute("SELECT * FROM users WHERE id = ?", (i,)).fetchone()) for i in (1, 2, 3))
    assert roles.access(conn, first)["is_owner"]
    assert "administrator" in {p for r in roles.access(conn, second)["roles"] for p in roles._perms(r)}
    assert roles.access(conn, third)["permissions"] == set(roles.LEARNING)
    conn.close()


def test_a_student_with_a_staff_role_stays_in_their_class(app):
    owner, admin, teacher, student = people(app)
    owner.post("/api/admin/roles", json={"name": "Class monitor", "permissions": ["view_analytics"]})
    give(owner, "Student", "Class monitor")
    student.patch("/api/me", json={"grade": 8})
    ask(student, "What is a fraction?")
    me = student.get("/api/me").get_json()["user"]
    assert me["staff"] and me["role"] == "student"  # opens the console, but still a learner
    assert [r["name"] for r in student.get("/api/leaderboard").get_json()["leaderboard"]] == ["Student"]
    assert any(s["name"] == "Student" for s in owner.get("/api/admin/students").get_json()["students"])


def test_staff_roles_stay_off_the_leaderboard(app):
    owner, admin, teacher, student = people(app)
    ask(student, "What is a fraction?")
    ask(teacher, "What is a fraction?")
    names = [row["name"] for row in student.get("/api/leaderboard").get_json()["leaderboard"]]
    assert names == ["Student"]
