from conftest import ask, register

from tatvax.ai import AIUnavailable


def test_first_account_becomes_teacher_and_keeps_guest_progress(client):
    ask(client, "What is a fraction?")  # creates a guest with progress
    response = register(client)
    assert response.status_code == 201
    user = response.get_json()["user"]
    assert user["role"] == "teacher"
    assert user["is_guest"] is False
    assert user["xp"] == 15
    assert len(client.get("/api/conversations").get_json()["conversations"]) == 1


def test_later_accounts_are_students_unless_they_have_the_teacher_code(app, client):
    register(client)
    second = app.test_client()
    assert register(second, email="ravi@example.test").get_json()["user"]["role"] == "student"
    third = app.test_client()
    assert register(third, email="t2@example.test", teacher_code="wrong").status_code == 400
    assert register(third, email="t2@example.test", teacher_code="staff-code").get_json()["user"]["role"] == "teacher"


def test_registration_validation(client):
    assert register(client, password="short").status_code == 400
    assert register(client, email="not-an-email").status_code == 400
    assert register(client, name="").status_code == 400
    register(client)
    other = client.application.test_client()
    assert register(other).status_code == 409  # duplicate email


def test_login_merges_guest_progress_into_the_account(app, client):
    register(client)
    client.post("/api/auth/logout", json={})

    device = app.test_client()
    ask(device, "What is a decimal?")
    response = device.post("/api/auth/login", json={"email": "asha@example.test", "password": "correct-horse"})
    assert response.status_code == 200
    assert response.get_json()["user"]["xp"] == 15
    assert len(device.get("/api/conversations").get_json()["conversations"]) == 1


def test_login_rejects_wrong_password(client):
    register(client)
    client.post("/api/auth/logout", json={})
    assert client.post("/api/auth/login", json={"email": "asha@example.test", "password": "nope"}).status_code == 401


def test_settings_update(client):
    register(client)
    user = client.patch("/api/me", json={"grade": 7, "theme": "dark", "language": "hi", "leaderboard": False}).get_json()["user"]
    assert (user["grade"], user["theme"], user["language"], user["leaderboard"]) == (7, "dark", "hi", False)
    assert client.patch("/api/me", json={"grade": 15}).status_code == 400
    assert client.patch("/api/me", json={"theme": "neon"}).status_code == 400
    assert client.patch("/api/me", json={"language": "xx"}).status_code == 400


def test_registered_students_appear_on_the_leaderboard(app, client):
    register(client)  # teacher
    student = app.test_client()
    register(student, name="Ravi", email="ravi@example.test")
    ask(student, "What is a fraction?")
    board = student.get("/api/leaderboard").get_json()
    assert board["leaderboard"][0]["name"] == "Ravi"
    student.patch("/api/me", json={"leaderboard": False})
    assert student.get("/api/leaderboard").get_json()["leaderboard"] == []


def test_teacher_console_requires_teacher_role(app, client):
    assert client.get("/api/admin/overview").status_code == 401
    register(client)
    assert client.get("/api/admin/overview").status_code == 200
    student = app.test_client()
    register(student, email="ravi@example.test")
    assert student.get("/api/admin/overview").status_code == 403
    assert student.put("/api/admin/documents/science", json={"title": "Hacked"}).status_code == 403


def test_teacher_edits_notes_and_the_tutor_uses_them(client):
    register(client)
    created = client.post("/api/admin/documents", json={
        "title": "Computer Science", "description": "Coding basics", "icon": "cpu", "color": "#123456",
        "body": "## Chapter 1: Algorithms\n\n**Binary Search**\nBinary search halves a sorted list at every step.\n",
    })
    assert created.status_code == 201
    slug = created.get_json()["document"]["slug"]
    assert slug == "computer-science"
    assert any(s["slug"] == slug for s in client.get("/api/bootstrap").get_json()["app"]["subjects"])

    events = ask(client, "How does binary search work?", subject=slug)
    assert "halves a sorted list" in events[1]["text"]

    assert client.put(f"/api/admin/documents/{slug}", json={"color": "red"}).status_code == 400
    assert client.put(f"/api/admin/documents/{slug}", json={"title": "CS"}).get_json()["document"]["title"] == "CS"
    assert client.delete(f"/api/admin/documents/{slug}", json={}).status_code == 200
    # The only help desk page can't be deleted.
    assert client.delete("/api/admin/documents/school-faq", json={}).status_code == 400


def test_teacher_overview_and_students(app, client):
    register(client)
    student = app.test_client()
    register(student, name="Ravi", email="ravi@example.test")
    ask(student, "What is a fraction?")
    overview = client.get("/api/admin/overview").get_json()
    assert overview["counts"]["students"] == 1
    assert overview["counts"]["questions"] == 1
    assert len(overview["questions_per_day"]) == 14
    students = client.get("/api/admin/students").get_json()["students"]
    assert students[0]["name"] == "Ravi" and students[0]["questions"] == 1


def test_teacher_saves_and_removes_the_nvidia_key(app, client, monkeypatch):
    assert client.get("/api/admin/ai").status_code == 401
    register(client)
    status = client.get("/api/admin/ai").get_json()
    assert status["ai"]["configured"] is False
    assert any(m["id"] == "google/gemma-4-31b-it" for m in status["models"])

    assert client.put("/api/admin/ai", json={"api_key": "short"}).status_code == 400
    assert client.put("/api/admin/ai", json={"model": "not a model"}).status_code == 400

    key = "nvapi-" + "a" * 40 + "WXYZ"
    saved = client.put("/api/admin/ai", json={"api_key": key, "model": "moonshotai/kimi-k2.6"}).get_json()["ai"]
    assert saved["configured"] and saved["source"] == "settings" and saved["model"] == "moonshotai/kimi-k2.6"
    assert saved["key_hint"] == "nvapi-…WXYZ"
    assert key not in client.get("/api/admin/ai").get_data(as_text=True)  # the key is never sent back
    assert client.get("/api/bootstrap").get_json()["app"]["ai_enabled"] is True

    service = app.extensions["tatvax"].ai
    monkeypatch.setattr(service, "complete", lambda *a, **k: "TatvaX is connected.")
    result = client.post("/api/admin/ai/test", json={}).get_json()
    assert result["ok"] and result["reply"] == "TatvaX is connected."

    def rejected(*_a, **_k):
        raise AIUnavailable("rejected: NVIDIA rejected the API key.", permanent=True)

    monkeypatch.setattr(service, "complete", rejected)
    assert client.post("/api/admin/ai/test", json={}).status_code == 502

    cleared = client.put("/api/admin/ai", json={"api_key": "", "model": ""}).get_json()["ai"]
    assert cleared["configured"] is False and cleared["model"] == "google/gemma-4-31b-it"
    assert client.get("/api/bootstrap").get_json()["app"]["ai_enabled"] is False


def test_students_cannot_change_ai_settings(app, client):
    register(client)
    student = app.test_client()
    register(student, email="ravi@example.test")
    assert student.put("/api/admin/ai", json={"api_key": "nvapi-" + "b" * 40}).status_code == 403
