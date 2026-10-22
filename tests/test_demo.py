"""The demo school builds, and its numbers add up the way the app's own rules would make them."""

import pytest

from tatvax import create_app, demo
from tatvax.db import connect


@pytest.fixture(scope="module")
def school(tmp_path_factory):
    folder = tmp_path_factory.mktemp("demo")
    accounts = demo.build(folder)
    app = create_app({"INSTANCE_DIR": folder, "DATABASE": str(folder / "tatvax.db"), "AI_ALLOWED": False,
                      "WEB_TRANSLATION": False, "TESTING": True})
    return app, folder, accounts


def login(app, email):
    client = app.test_client()
    response = client.post("/api/auth/login", json={"email": email, "password": demo.DEMO_PASSWORD})
    assert response.status_code == 200, email
    return client


def test_every_account_signs_in_with_the_demo_password(school):
    app, _folder, accounts = school
    text = accounts.read_text(encoding="utf-8")
    for _name, email, *_rest in demo.STAFF + demo.STUDENTS:
        assert email in text
    login(app, "principal@sunrise.school")
    login(app, "riya@sunrise.school")


def test_the_role_ladder(school):
    app, *_ = school
    principal = login(app, "principal@sunrise.school")
    ladder = [r["name"] for r in principal.get("/api/admin/roles").get_json()["roles"]]
    assert ladder == ["Owner", "Admin", "Head of Department", "Teacher", "Content Editor", "Class Monitor", "Student"]
    assert principal.get("/api/me").get_json()["user"]["is_owner"]
    teacher = login(app, "rahul.verma@sunrise.school")
    assert teacher.get("/api/admin/overview").status_code == 200 and teacher.get("/api/admin/ai").status_code == 403
    monitor = login(app, "kiran@sunrise.school").get("/api/me").get_json()["user"]
    assert monitor["staff"] and monitor["role"] == "student" and monitor["top_role"]["name"] == "Class Monitor"


def test_the_school_looks_lived_in(school):
    app, *_ = school
    principal = login(app, "principal@sunrise.school")
    counts = principal.get("/api/admin/overview").get_json()["counts"]
    assert counts["students"] == len(demo.STUDENTS) and counts["questions"] > 300 and counts["quizzes"] > 50
    assert len(principal.get("/api/leaderboard").get_json()["leaderboard"]) == 10
    assert principal.get("/api/admin/feedback").get_json()["feedback"]
    assignments = principal.get("/api/admin/assignments").get_json()["assignments"]
    assert len(assignments) == 6 and any(a["done"] for a in assignments)

    star = login(app, "aarav@sunrise.school")
    progress = star.get("/api/progress").get_json()["progress"]
    assert progress["streak"]["current"] >= 10 and sum(b["earned"] for b in progress["badges"]) >= 5
    assert star.get("/api/review").get_json()["summary"]["total"] > 0
    assert star.get("/api/todos").get_json()["todos"]
    assert star.get("/api/conversations").get_json()["conversations"]


def test_xp_and_activity_follow_the_rules(school):
    _app, folder, _accounts = school
    conn = connect(str(folder / "tatvax.db"))
    try:
        mismatched = conn.execute(
            "SELECT COUNT(*) FROM users u WHERE xp != (SELECT COALESCE(SUM(points), 0) FROM xp_events x WHERE x.user_id = u.id)"
        ).fetchone()[0]
        assert mismatched == 0
        over_cap = conn.execute(
            """SELECT COUNT(*) FROM (SELECT user_id, substr(created_at, 1, 10) AS day, SUM(points) AS p FROM xp_events
               WHERE reason = 'question' GROUP BY user_id, day) WHERE p > 100""").fetchone()[0]
        assert over_cap == 0
        logged = conn.execute("SELECT COUNT(*) FROM question_log").fetchone()[0]
        asked = conn.execute("SELECT COUNT(*) FROM messages WHERE role = 'user'").fetchone()[0]
        assert logged == asked
        assert conn.execute("SELECT COUNT(*) FROM messages WHERE language != 'en'").fetchone()[0] > 0
    finally:
        conn.close()


def test_one_click_switching_only_in_demo_mode(school):
    app, folder, _accounts = school
    # The school fixture runs without demo mode: the switcher doesn't exist.
    client = app.test_client()
    assert client.get("/api/demo").status_code == 404
    assert client.post("/api/demo/switch", json={"persona": "principal"}).status_code == 404
    assert client.get("/api/bootstrap").get_json()["app"]["demo"] is False

    demo_app = create_app({"INSTANCE_DIR": folder, "DATABASE": str(folder / "tatvax.db"), "AI_ALLOWED": False,
                           "WEB_TRANSLATION": False, "TESTING": True, "DEMO_MODE": True})
    client = demo_app.test_client()
    assert client.get("/api/bootstrap").get_json()["app"]["demo"] is True
    listed = client.get("/api/demo").get_json()["personas"]
    assert [p["key"] for p in listed] == [p["key"] for p in demo.PERSONAS]
    assert all("email" not in p for p in listed)
    for persona in demo.PERSONAS:
        response = client.post("/api/demo/switch", json={"persona": persona["key"]})
        assert response.status_code == 200 and response.get_json()["start"] == persona["start"]
        user = client.get("/api/me").get_json()["user"]
        assert (user["email"] if user else None) == persona["email"]
        assert next(p for p in client.get("/api/demo").get_json()["personas"] if p["active"])["key"] == persona["key"]
    # Only the listed accounts: no switching into anyone else's account.
    assert client.post("/api/demo/switch", json={"persona": "riya@sunrise.school"}).status_code == 400


def test_an_existing_demo_is_kept_unless_reset(school):
    _app, folder, _accounts = school
    with pytest.raises(FileExistsError):
        demo.build(folder)
