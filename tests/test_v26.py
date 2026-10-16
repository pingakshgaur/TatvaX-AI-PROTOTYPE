import base64

from conftest import ask, register, stream_events

from tatvax import db as tatvax_db
from tatvax import languages
from tatvax.ai import AIService, ImagesUnsupported
from tatvax.security import RateLimiter

PNG = "data:image/png;base64," + base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"0" * 64).decode()


def finish_quiz(client, subject="science", count=5, wrong=True):
    quiz = client.post("/api/quiz", json={"subjects": [subject], "count": count, "mode": "exam", "language": "en"}).get_json()["quiz"]
    detail_answers = [None] * len(quiz["questions"]) if wrong else None
    result = client.post(f"/api/quiz/{quiz['id']}/submit", json={"answers": detail_answers or [0] * len(quiz["questions"])})
    return quiz, result.get_json()


# --------------------------------------------------------------------------- review deck

def test_missed_questions_become_review_cards(client):
    quiz, result = finish_quiz(client)
    deck = client.get("/api/review").get_json()
    assert deck["summary"]["due"] == len(quiz["questions"]) == deck["summary"]["total"]
    card = deck["cards"][0]
    assert {"question", "options", "box"} <= set(card) and "answer_index" not in card

    # Taking the same assessment again doesn't duplicate cards.
    client.post(f"/api/quiz/{quiz['id']}/retake", json={})
    assert client.get("/api/review").get_json()["summary"]["total"] == len(quiz["questions"])


def test_reviewing_moves_cards_through_the_boxes(client):
    finish_quiz(client)
    card = client.get("/api/review").get_json()["cards"][0]
    wrong = client.post(f"/api/review/{card['id']}", json={"choice": 0}).get_json()
    right_choice = wrong["answer_index"]
    if wrong["correct"]:  # choice 0 happened to be right
        assert wrong["box"] == 1
    else:
        assert wrong["box"] == 0 and wrong["due"] > tatvax_db.today()

    right = client.post(f"/api/review/{card['id']}", json={"choice": right_choice}).get_json()
    assert right["correct"] and right["box"] >= 1 and right["xp_gained"] == 2
    assert client.post(f"/api/review/{card['id']}", json={"choice": 9}).status_code == 400
    assert client.delete(f"/api/review/{card['id']}").status_code == 200
    assert client.post(f"/api/review/{card['id']}", json={"choice": 0}).status_code == 404


def test_review_cards_follow_a_guest_into_their_account(app, client):
    register(client)
    client.post("/api/auth/logout", json={})
    device = app.test_client()
    finish_quiz(device)
    device.post("/api/auth/login", json={"email": "asha@example.test", "password": "correct-horse"})
    assert device.get("/api/review").get_json()["summary"]["total"] == 5


# --------------------------------------------------------------------------- assignments

def test_teacher_sets_an_assessment_and_sees_who_finished(app, client):
    register(client, name="Ms Rao", email="rao@example.test")  # first account: teacher
    made = client.post("/api/admin/assignments", json={
        "title": "Energy revision", "kind": "quiz", "subjects": ["science"], "count": 5, "grade": 7,
        "due_date": "2026-10-30", "mode": "exam",
    })
    assert made.status_code == 201
    assignment = made.get_json()["assignment"]
    assert assignment["questions"] == 5 and assignment["grade"] == 7

    student = app.test_client()
    register(student, name="Ravi", email="ravi@example.test")
    student.patch("/api/me", json={"grade": 7})
    other = app.test_client()
    register(other, name="Meera", email="meera@example.test")
    other.patch("/api/me", json={"grade": 8})

    mine = student.get("/api/assignments").get_json()["assignments"]
    assert [a["title"] for a in mine] == ["Energy revision"] and mine[0]["status"]["state"] == "todo"
    assert other.get("/api/assignments").get_json()["assignments"] == []

    quiz = student.post(f"/api/assignments/{assignment['id']}/start", json={}).get_json()["quiz"]
    assert quiz["mode"] == "exam" and len(quiz["questions"]) == 5
    student.post(f"/api/quiz/{quiz['id']}/submit", json={"answers": [0, 0, 0, 0, 0]})
    status = student.get("/api/assignments").get_json()["assignments"][0]["status"]
    assert status["state"] == "done" and status["total"] == 5

    overview = client.get("/api/admin/assignments").get_json()["assignments"][0]
    assert overview["students"] == 1 and overview["done"] == 1
    progress = client.get(f"/api/admin/assignments/{assignment['id']}").get_json()
    assert progress["students"][0]["name"] == "Ravi" and len(progress["assignment"]["preview"]) == 5
    assert student.get("/api/admin/assignments").status_code == 403


def test_reading_assignments_are_ticked_off(app, client):
    register(client, name="Ms Rao", email="rao@example.test")
    reading = client.post("/api/admin/assignments", json={"title": "Read chapter 2", "kind": "reading", "subjects": ["english"]})
    rid = reading.get_json()["assignment"]["id"]
    student = app.test_client()
    register(student, name="Ravi", email="ravi@example.test")
    assert student.post(f"/api/assignments/{rid}/done", json={}).get_json()["status"]["state"] == "done"
    assert student.post(f"/api/assignments/{rid}/start", json={}).status_code == 404
    client.patch(f"/api/admin/assignments/{rid}", json={"archived": True})
    assert student.get("/api/assignments").get_json()["assignments"] == []
    assert client.post("/api/admin/assignments", json={"title": "x", "kind": "essay", "subjects": ["english"]}).status_code == 400


# --------------------------------------------------------------------------- reports

def test_progress_report(app, client):
    register(client, name="Ms Rao", email="rao@example.test")
    student = app.test_client()
    register(student, name="Ravi", email="ravi@example.test")
    ask(student, "What is a fraction?")
    finish_quiz(student, "mathematics")
    report = student.get("/api/report").get_json()["report"]
    assert report["student"]["name"] == "Ravi"
    maths = next(s for s in report["subjects"] if s["slug"] == "mathematics")
    assert maths["questions"] == 1 and maths["assessments"] == 1 and maths["to_review"] == 5
    assert len(report["activity"]) == 30 and report["recent"][0]["total"] == 5

    ravi_id = report["student"]["id"]
    assert client.get(f"/api/admin/students/{ravi_id}/report").get_json()["report"]["student"]["name"] == "Ravi"
    assert student.get(f"/api/admin/students/{ravi_id}/report").status_code == 403


# --------------------------------------------------------------------------- to-do reminders and links

def test_todo_summary_and_links(client):
    today = tatvax_db.today()
    client.post("/api/todos", json={"title": "Overdue", "due_date": "2020-01-01"})
    client.post("/api/todos", json={"title": "Due today", "due_date": today, "link": "/assessments/review/1"})
    client.post("/api/todos", json={"title": "Someday"})
    summary = client.get("/api/todos/summary").get_json()
    assert summary["overdue"] == 1 and summary["today"] == 1 and summary["open"] == 3
    assert [t["title"] for t in summary["next"]] == ["Overdue", "Due today"]
    assert summary["next"][1]["link"] == "/assessments/review/1"
    for bad in ("https://evil.example", "//evil.example", "javascript:alert(1)"):
        assert client.post("/api/todos", json={"title": "x", "link": bad}).status_code == 400


# --------------------------------------------------------------------------- photos

def test_photo_questions_are_validated_and_explained_without_ai(client):
    assert client.post("/api/chat", json={"message": "hi", "image": "data:text/html;base64,PGI+"}).status_code == 400
    assert client.post("/api/chat", json={"image": "data:image/png;base64," + "A" * 1_600_000}).status_code == 400
    events = stream_events(client.post("/api/chat", json={"message": "", "image": PNG, "mode": "subject", "subject": "science"}))
    assert "picture" in events[-2]["text"] or "picture" in "".join(e.get("text", "") for e in events)
    convo = client.get(f"/api/conversations/{events[0]['conversation_id']}").get_json()
    assert convo["messages"][0]["content"].startswith("[Photo] ")


def test_images_are_sent_in_each_providers_format():
    messages = [{"role": "user", "content": "What is this?", "image": {"media_type": "image/png", "data": "QUJD"}}]
    openai_style = AIService._with_images("openai", messages)[0]["content"]
    assert openai_style[1] == {"type": "image_url", "image_url": {"url": "data:image/png;base64,QUJD"}}
    claude_style = AIService._with_images("anthropic", messages)[0]["content"]
    assert claude_style[0]["source"] == {"type": "base64", "media_type": "image/png", "data": "QUJD"}
    assert AIService._with_images("openai", [{"role": "user", "content": "hi"}]) == [{"role": "user", "content": "hi"}]


def test_models_that_cannot_read_pictures_get_a_clear_message(monkeypatch):
    service = AIService("nvapi-" + "z" * 40)

    def rejecting(*_args, **_kwargs):
        from tatvax.ai import AIUnavailable
        raise AIUnavailable("NVIDIA API error (400): image input not supported")
        yield  # pragma: no cover

    monkeypatch.setattr(service, "_stream", rejecting)
    messages = [{"role": "user", "content": "x", "image": {"media_type": "image/png", "data": "QUJD"}}]
    try:
        list(service.stream_reply("s", messages))
    except ImagesUnsupported as exc:
        assert "can't read pictures" in str(exc)
    else:
        raise AssertionError("expected ImagesUnsupported")


# --------------------------------------------------------------------------- languages, limits, time

def test_new_languages():
    assert {"ne", "sa", "gom"} <= set(languages.LANGUAGES)
    assert languages.detect_language("तपाईं कस्तो हुनुहुन्छ? म ठिक छ") == "ne"
    assert languages.detect_language("मला गणित आवडते आणि मी अभ्यास करतो") == "mr"


def test_shared_rate_limit_is_kept_in_the_database(tmp_path):
    path = str(tmp_path / "limits.db")
    first, second = RateLimiter(), RateLimiter()  # two worker processes
    first.configure(path)
    second.configure(path)
    assert first.allow("chat:1", 2) and second.allow("chat:1", 2)
    assert not first.allow("chat:1", 2) and not second.allow("chat:1", 2)
    assert first.allow("chat:2", 2)


def test_days_follow_the_school_clock():
    assert tatvax_db.now_iso().endswith("+05:30")
    assert tatvax_db.today() == tatvax_db.now_iso()[:10]
