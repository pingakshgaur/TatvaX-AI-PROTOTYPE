"""Regression tests for the bugs fixed in 2.6.1."""

import json

from conftest import ask, register

from tatvax import db as tatvax_db
from tatvax import knowledge, languages
from tatvax.ai import AIService, AIUnavailable
from tatvax.config import _load_secret_key


def new_quiz(client, mode="exam", count=5, subject="mathematics"):
    response = client.post("/api/quiz", json={"subjects": [subject], "count": count, "mode": mode, "language": "en"})
    assert response.status_code == 201, response.get_data(as_text=True)
    return response.get_json()["quiz"]


def set_created(app, quiz_id, seconds_ago):
    """Pretend an assessment was started some time ago."""
    from datetime import datetime, timedelta

    conn = tatvax_db.connect(app.config["DATABASE"])
    started = (datetime.now(tatvax_db.SCHOOL_TZ) - timedelta(seconds=seconds_ago)).isoformat(timespec="seconds")
    conn.execute("UPDATE quizzes SET created_at = ? WHERE id = ?", (started, quiz_id))
    conn.commit()
    conn.close()


# --------------------------------------------------------------------------- broken features

def test_photos_can_be_prepared_in_the_browser(client):
    # The browser shrinks a photo through a blob: URL before sending it.
    csp = client.get("/").headers["Content-Security-Policy"]
    img_src = next(part for part in csp.split("; ") if part.startswith("img-src"))
    assert "blob:" in img_src and "data:" in img_src


def test_anthropic_is_a_dependency():
    from pathlib import Path

    requirements = (Path(__file__).resolve().parent.parent / "requirements.txt").read_text(encoding="utf-8")
    assert any(line.startswith("anthropic") for line in requirements.splitlines())


def test_stopping_an_answer_keeps_the_question(app, client):
    response = client.post("/api/chat", json={"message": "What is a fraction?", "mode": "subject", "subject": "mathematics"},
                           buffered=False)
    next(iter(response.response))  # the "start" event, then hang up like the Stop button
    response.close()
    conversations = client.get("/api/conversations").get_json()["conversations"]
    assert len(conversations) == 1
    messages = client.get(f"/api/conversations/{conversations[0]['id']}").get_json()["messages"]
    assert [m["role"] for m in messages][:1] == ["user"] and messages[0]["content"] == "What is a fraction?"


def test_chats_in_a_deleted_subject_carry_on(app, client):
    register(client)  # teacher
    start = ask(client, "What is a fraction?")
    conversation_id = start[0]["conversation_id"]
    assert client.delete("/api/admin/documents/mathematics").status_code == 200
    events = ask(client, "And a decimal?", conversation_id=conversation_id)
    assert events[-1]["type"] == "done"


def test_unfinished_assessments_can_be_resumed(client):
    quiz = new_quiz(client, mode="practice")
    first = client.post(f"/api/quiz/{quiz['id']}/answer", json={"index": 0, "choice": 1}).get_json()
    detail = client.get(f"/api/quiz/{quiz['id']}").get_json()["quiz"]
    progress = detail["progress"]
    assert [a["index"] for a in progress["answers"]] == [0]
    assert progress["answers"][0]["answer_index"] == first["answer_index"]
    # Exam answers stay hidden until the end.
    exam = new_quiz(client, mode="exam")
    assert client.get(f"/api/quiz/{exam['id']}").get_json()["quiz"]["progress"]["answers"] == []


def test_timed_assessments_report_the_time_left(app, client):
    quiz = new_quiz(client, mode="timed")
    set_created(app, quiz["id"], 100)
    progress = client.get(f"/api/quiz/{quiz['id']}").get_json()["quiz"]["progress"]
    assert quiz["time_limit"] - 105 <= progress["seconds_left"] <= quiz["time_limit"] - 99


def test_a_half_done_assignment_is_resumed_not_restarted(app, client):
    register(client)  # teacher
    client.post("/api/admin/assignments", json={"title": "Fractions", "kind": "quiz", "subjects": ["mathematics"],
                                                "count": 5, "mode": "practice"})
    assignment = client.get("/api/admin/assignments").get_json()["assignments"][0]
    student = app.test_client()
    register(student, name="Ravi", email="ravi@example.test")
    quiz = student.post(f"/api/assignments/{assignment['id']}/start", json={}).get_json()["quiz"]
    student.post(f"/api/quiz/{quiz['id']}/answer", json={"index": 0, "choice": 0})
    again = student.post(f"/api/assignments/{assignment['id']}/start", json={}).get_json()["quiz"]
    assert again["id"] == quiz["id"] and len(again["progress"]["answers"]) == 1


# --------------------------------------------------------------------------- fairness

def test_exam_answers_cannot_be_peeked_one_at_a_time(client):
    for mode in ("exam", "timed"):
        quiz = new_quiz(client, mode=mode)
        response = client.post(f"/api/quiz/{quiz['id']}/answer", json={"index": 0, "choice": 0})
        assert response.status_code == 400 and "answer_index" not in response.get_json()
    practice = new_quiz(client, mode="practice")
    assert client.post(f"/api/quiz/{practice['id']}/submit", json={"answers": [0] * 5}).status_code == 400


def test_retaking_can_not_farm_xp(client):
    quiz = new_quiz(client)
    finished = client.post(f"/api/quiz/{quiz['id']}/submit", json={"answers": [0] * 5}).get_json()
    gained = finished["xp_gained"]
    statuses = []
    for _ in range(12):
        response = client.post(f"/api/quiz/{quiz['id']}/retake", json={})
        statuses.append(response.status_code)
        if response.status_code == 201:
            again = response.get_json()["quiz"]
            gained += client.post(f"/api/quiz/{again['id']}/submit", json={"answers": [0] * 5}).get_json()["xp_gained"]
    assert 429 in statuses  # retakes share the assessment rate limit
    from tatvax.gamification import DAILY_BONUS_XP, QUIZ_XP_DAILY_CAP

    assert gained <= QUIZ_XP_DAILY_CAP + DAILY_BONUS_XP + 15  # 15: daily-goal bonus


def test_late_timed_submissions_get_no_bonus(app, client):
    quiz = new_quiz(client, mode="timed", count=3)
    detail = client.get(f"/api/quiz/{quiz['id']}").get_json()["quiz"]
    set_created(app, quiz["id"], quiz["time_limit"] + 600)
    conn = tatvax_db.connect(app.config["DATABASE"])
    answers = [q["answer_index"] for q in json.loads(conn.execute("SELECT questions_json FROM quizzes WHERE id = ?",
                                                                  (quiz["id"],)).fetchone()[0])]
    conn.close()
    result = client.post(f"/api/quiz/{quiz['id']}/submit", json={"answers": answers, "duration_s": 5}).get_json()
    assert result["score"] == 3 and result["late"] is True
    assert result["duration_s"] >= quiz["time_limit"] + 600  # the server's clock, not the client's
    assert not any(b["id"] == "speedster" for b in result["badges"])
    assert detail["mode"] == "timed"


def test_a_quiz_can_only_be_finished_once(app, client):
    from tatvax.quiz import QuizError

    quiz = new_quiz(client)
    services = app.extensions["tatvax"]
    with app.test_request_context():
        conn = tatvax_db.get_db()
        user = conn.execute("SELECT * FROM users").fetchone()
        row = conn.execute("SELECT * FROM quizzes WHERE id = ?", (quiz["id"],)).fetchone()
        questions = json.loads(row["questions_json"])
        services.quizmaster._finish(conn, user, row, questions, {}, None)
        conn.commit()
        try:
            services.quizmaster._finish(conn, user, row, questions, {}, None)  # same stale row, as in a race
            raise AssertionError("finished twice")
        except QuizError:
            pass


def test_assignment_attempts_are_kept_and_scored_by_the_first_try(app, client):
    register(client)  # teacher
    client.post("/api/admin/assignments", json={"title": "Fractions", "kind": "quiz", "subjects": ["mathematics"],
                                                "count": 3, "mode": "exam"})
    assignment = client.get("/api/admin/assignments").get_json()["assignments"][0]
    student = app.test_client()
    register(student, name="Ravi", email="ravi@example.test")
    quiz = student.post(f"/api/assignments/{assignment['id']}/start", json={}).get_json()["quiz"]
    student.post(f"/api/quiz/{quiz['id']}/submit", json={"answers": [None] * 3})
    assert student.delete(f"/api/quiz/{quiz['id']}").status_code == 409

    # A second attempt with every answer right doesn't replace the first score.
    retry = student.post(f"/api/assignments/{assignment['id']}/start", json={}).get_json()["quiz"]
    conn = tatvax_db.connect(app.config["DATABASE"])
    answers = [q["answer_index"] for q in json.loads(conn.execute("SELECT questions_json FROM quizzes WHERE id = ?",
                                                                  (retry["id"],)).fetchone()[0])]
    conn.close()
    student.post(f"/api/quiz/{retry['id']}/submit", json={"answers": answers})
    row = client.get(f"/api/admin/assignments/{assignment['id']}").get_json()["students"][0]
    assert row["state"] == "done" and row["score"] == 0 and row["best_score"] == 3 and row["attempts"] == 2


# --------------------------------------------------------------------------- security and privacy

def test_signing_up_while_signed_in_never_overwrites_the_account(app, client):
    register(client)  # the first account: a teacher
    response = client.post("/api/auth/register", json={"name": "Oops", "email": "new@example.test", "password": "password123"})
    assert response.status_code == 409
    login = app.test_client().post("/api/auth/login", json={"email": "asha@example.test", "password": "correct-horse"})
    assert login.status_code == 200 and login.get_json()["user"]["role"] == "teacher"


def test_duplicate_email_is_a_clear_error(app, client):
    register(client)
    other = app.test_client()
    assert register(other, name="Copy").status_code == 409


def test_server_keys_are_never_revealed(app, client, monkeypatch):
    register(client)
    ai = app.extensions["tatvax"].ai
    ai.env_keys["groq"] = "gsk_" + "s" * 40
    ai.configure_provider("groq", None, None, None)
    revealed = client.get("/api/admin/ai/key?provider=groq").get_json()
    assert revealed["api_key"] is None and revealed["source"] == "environment"


def test_ai_server_address_cannot_point_at_cloud_metadata(client):
    register(client)
    for url in ("http://169.254.169.254/v1", "http://metadata.google.internal/", "http://[fe80::1]/v1"):
        response = client.put("/api/admin/ai", json={"provider": "custom", "base_url": url})
        assert response.status_code == 400, url
    assert client.put("/api/admin/ai", json={"provider": "custom", "base_url": "http://192.168.1.20:8000/v1"}).status_code == 200


def test_leaderboard_needs_a_session_and_lists_students_only(app, client):
    register(client)  # teacher
    ask(client, "What is a fraction?")
    student = app.test_client()
    register(student, name="Ravi", email="ravi@example.test")
    ask(student, "What is a fraction?")
    assert app.test_client().get("/api/leaderboard").get_json()["leaderboard"] == []
    names = [row["name"] for row in student.get("/api/leaderboard").get_json()["leaderboard"]]
    assert names == ["Ravi"]


def test_web_translation_can_be_turned_off(app):
    from tatvax.translation import TranslationError, Translator

    translator = Translator(AIService(allowed=False), web=False)
    try:
        translator.translate("Hello", "hi", "en")
        raise AssertionError("translated without the AI")
    except TranslationError:
        pass


# --------------------------------------------------------------------------- correct numbers

def test_report_counts_every_question(client):
    ask(client, "What is a fraction?", subject="all")
    ask(client, "What is photosynthesis?", subject="all")
    report = client.get("/api/report").get_json()["report"]
    assert report["totals"]["questions"] == 2


def test_mixed_assessments_score_each_subject_on_its_own_questions(app, client):
    response = client.post("/api/quiz", json={"subjects": ["mathematics", "science"], "count": 6, "mode": "exam", "language": "en"})
    quiz = response.get_json()["quiz"]
    conn = tatvax_db.connect(app.config["DATABASE"])
    questions = json.loads(conn.execute("SELECT questions_json FROM quizzes WHERE id = ?", (quiz["id"],)).fetchone()[0])
    conn.close()
    # Every maths question right, every science question wrong.
    answers = [q["answer_index"] if q["subject"] == "mathematics" else (q["answer_index"] + 1) % 4 for q in questions]
    client.post(f"/api/quiz/{quiz['id']}/submit", json={"answers": answers})
    subjects = {s["slug"]: s for s in client.get("/api/report").get_json()["report"]["subjects"]}
    assert subjects["mathematics"]["average"] == 100 and subjects["science"]["average"] == 0
    overview = {s["slug"]: s for s in client.get("/api/subjects/overview").get_json()["subjects"]}
    assert overview["mathematics"]["average"] == 100 and overview["science"]["average"] == 0


def test_students_without_a_class_only_see_work_for_everyone(app, client):
    register(client)  # teacher
    client.post("/api/admin/assignments", json={"title": "Class 9 reading", "kind": "reading", "subjects": ["science"], "grade": 9})
    client.post("/api/admin/assignments", json={"title": "Everyone", "kind": "reading", "subjects": ["science"]})
    student = app.test_client()
    register(student, name="Ravi", email="ravi@example.test")
    titles = [a["title"] for a in student.get("/api/assignments").get_json()["assignments"]]
    assert titles == ["Everyone"]
    student.patch("/api/me", json={"grade": 9})
    assert len(student.get("/api/assignments").get_json()["assignments"]) == 2


def test_notes_read_are_saved_on_the_account(app, client):
    assert client.put("/api/library/science/read", json={"read": ["ch-0", "ch-2"]}).status_code == 200
    assert client.put("/api/library/science/read", json={"read": ["<script>"]}).status_code == 400
    register(client)
    other_device = app.test_client()
    other_device.post("/api/auth/login", json={"email": "asha@example.test", "password": "correct-horse"})
    assert other_device.get("/api/library/science/read").get_json()["read"] == ["ch-0", "ch-2"]
    overview = {s["slug"]: s for s in other_device.get("/api/subjects/overview").get_json()["subjects"]}
    assert overview["science"]["read"] == 2


def test_bootstrap_tells_the_app_the_school_day(client):
    data = client.get("/api/bootstrap").get_json()["app"]
    assert data["today"] == tatvax_db.today() and isinstance(data["utc_offset_minutes"], int)


# --------------------------------------------------------------------------- languages

def test_notes_in_indian_scripts_are_searchable(client):
    register(client)
    created = client.post("/api/admin/documents", json={
        "title": "विज्ञान", "kind": "subject",
        "body": "## प्रकाश संश्लेषण\nपौधे सूर्य के प्रकाश से भोजन बनाते हैं। यह प्रक्रिया पत्तियों में होती है।",
    }).get_json()["document"]
    assert created["slug"] == "विज्ञान"
    hits = client.get("/api/search", query_string={"q": "प्रकाश संश्लेषण क्या है"}).get_json()["results"]
    assert hits and hits[0]["slug"] == "विज्ञान"


def test_tokenizer_keeps_indic_words_whole():
    assert knowledge.tokenize("प्रकाश संश्लेषण") == ["प्रकाश", "संश्लेषण"]
    assert knowledge.tokenize("What are fractions?") == ["fraction"]


def test_hindi_words_that_contain_marathi_words_stay_hindi():
    assert languages.detect_language("देश पर हमला हुआ") == "hi"
    assert languages.detect_language("कमला स्कूल जाती है") == "hi"
    assert languages.detect_language("मला गणित आवडते") == "mr"


def test_bank_quizzes_are_translated_in_one_request(app, client, monkeypatch):
    calls = []

    def fake(text, target, source="auto"):
        calls.append(text)
        return "\n".join(f"[{target}] {line}" for line in text.split("\n")), "fake"

    monkeypatch.setattr(app.extensions["tatvax"].translator, "translate", fake)
    quiz = client.post("/api/quiz", json={"subjects": ["science"], "count": 5, "language": "hi"}).get_json()["quiz"]
    assert len(calls) == 1 and quiz["questions"][0]["question"].startswith("[hi] ")


# --------------------------------------------------------------------------- deployment

def test_ai_settings_saved_by_another_process_are_picked_up(app, client):
    register(client)
    ai = app.extensions["tatvax"].ai
    assert ai.active == "nvidia"
    conn = tatvax_db.connect(app.config["DATABASE"])  # another worker saves new settings
    tatvax_db.set_setting(conn, "api_key:groq", "gsk_" + "k" * 40)
    tatvax_db.set_setting(conn, "ai_provider", "groq")
    conn.commit()
    conn.close()
    client.get("/api/me")
    assert ai.active == "groq" and ai.states["groq"].source == "settings"


def test_testing_a_provider_does_not_switch_the_active_one(monkeypatch):
    ai = AIService("nvapi-" + "k" * 40)
    ai.env_keys["groq"] = "gsk_" + "k" * 40
    ai.configure_provider("groq", None, None, None)
    seen = []

    def fake_complete(system, prompt, max_tokens=2048, json_mode=False, pid=None):
        seen.append((pid, ai.active))
        return "TatvaX is connected."

    monkeypatch.setattr(ai, "complete", fake_complete)
    ai.test("groq")
    assert seen == [("groq", "nvidia")]


def test_photo_errors_only_blame_the_picture_when_it_was_rejected(monkeypatch):
    ai = AIService("nvapi-" + "k" * 40)

    def timeout(*_args, **_kwargs):
        raise AIUnavailable("Couldn't reach NVIDIA.")
        yield  # pragma: no cover

    monkeypatch.setattr(ai, "_stream", timeout)
    messages = [{"role": "user", "content": "x", "image": {"media_type": "image/png", "data": "QUJD"}}]
    try:
        list(ai.stream_reply("s", messages))
    except AIUnavailable as exc:
        assert type(exc) is AIUnavailable  # not ImagesUnsupported
    else:
        raise AssertionError("expected AIUnavailable")


def test_workers_starting_together_share_one_secret_key(tmp_path, monkeypatch):
    monkeypatch.delenv("TATVAX_SECRET_KEY", raising=False)
    first = _load_secret_key(tmp_path)
    assert _load_secret_key(tmp_path) == first and len(first) == 64
    assert [p.name for p in tmp_path.iterdir()] == ["secret_key"]


def test_new_bundled_notes_are_imported_on_upgrade(app, tmp_path):
    content = tmp_path / "content"
    (content / "subjects").mkdir(parents=True)
    (content / "helpdesk").mkdir()
    conn = tatvax_db.connect(app.config["DATABASE"])
    assert knowledge.seed_documents(conn, content) == 0
    (content / "subjects" / "computers.md").write_text("---\ntitle: Computers\n---\n## Chapter 1\nComputers follow instructions.\n",
                                                       encoding="utf-8")
    assert knowledge.seed_documents(conn, content) == 1
    conn.execute("DELETE FROM documents WHERE slug = 'computers'")  # a teacher deletes it
    assert knowledge.seed_documents(conn, content) == 0  # and it stays deleted
    conn.close()


def test_duplicating_respects_the_task_limit(client, monkeypatch):
    from tatvax import todos

    monkeypatch.setattr(todos, "MAX_TODOS", 1)
    todo = client.post("/api/todos", json={"title": "Revise"}).get_json()["todo"]
    assert client.post(f"/api/todos/{todo['id']}/duplicate", json={}).status_code == 400


def test_failed_photo_answers_earn_no_xp(client):
    import base64

    png = "data:image/png;base64," + base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"0" * 64).decode()
    events = ask(client, "", image=png)  # no AI key in tests, so the photo can't be read
    assert any(e["type"] == "replace" and "picture" in e["text"] for e in events)
    assert events[-1]["xp_gained"] == 0 and events[-1]["badges"] == []
