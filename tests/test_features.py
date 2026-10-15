from conftest import ask, register

from tatvax.followups import MARKER, FollowupSplitter, parse


def test_followup_splitter_hides_the_marker_across_chunks():
    splitter = FollowupSplitter()
    chunks = ["The answer is 4.", "\n@@FOLL", "OWUPS@@\nWhat is 5+5?\n", "- Why does 2+2=4?\n3. Quiz me"]
    visible = "".join(splitter.feed(c) for c in chunks)
    rest, block = splitter.finish()
    assert visible + rest == "The answer is 4.\n"
    assert MARKER not in visible
    assert parse(block, asked=["what is 5+5"]) == ["Why does 2+2=4?", "Quiz me"]


def test_answers_come_with_new_follow_up_suggestions(client):
    events = ask(client, "What are the parts of speech?", subject="english")
    done = events[-1]
    assert 2 <= len(done["suggestions"]) <= 3
    assert all(s.lower() != "what are the parts of speech?" for s in done["suggestions"])
    detail = client.get(f"/api/conversations/{events[0]['conversation_id']}").get_json()
    assert detail["messages"][-1]["suggestions"] == done["suggestions"]


def test_multi_subject_assessment_with_custom_length(client):
    quiz = client.post("/api/quiz", json={
        "subjects": ["mathematics", "science", "english"], "count": 12, "difficulty": "mixed", "language": "en",
    }).get_json()["quiz"]
    assert len(quiz["questions"]) == 12
    assert {q["subject"] for q in quiz["questions"]} == {"mathematics", "science", "english"}
    assert quiz["subject"] == "mixed" and quiz["mode"] == "practice"


def test_offline_bank_shortage_is_explained(client):
    quiz = client.post("/api/quiz", json={"subjects": ["science"], "count": 30, "language": "en"}).get_json()["quiz"]
    assert len(quiz["questions"]) == 14  # the whole offline bank for science
    assert "Only 14 questions" in quiz["notice"]


def test_count_is_clamped(client):
    quiz = client.post("/api/quiz", json={"subjects": ["science"], "count": 1, "language": "en"}).get_json()["quiz"]
    assert len(quiz["questions"]) == 3


def test_exam_mode_grades_everything_at_once_and_retry_mistakes(client):
    quiz = client.post("/api/quiz", json={"subjects": ["english"], "count": 5, "mode": "exam", "language": "en"}).get_json()["quiz"]
    assert quiz["mode"] == "exam" and quiz["time_limit"] is None
    result = client.post(f"/api/quiz/{quiz['id']}/submit", json={"answers": [0, 1, None, 2, 3], "duration_s": 95}).get_json()
    assert result["total"] == 5 and len(result["results"]) == 5
    assert result["results"][2]["choice"] is None and result["results"][2]["correct"] is False
    assert result["breakdown"][0]["total"] == 5
    assert client.post(f"/api/quiz/{quiz['id']}/submit", json={"answers": [0] * 5}).status_code == 400  # already finished

    wrong = sum(1 for r in result["results"] if not r["correct"])
    retry = client.post(f"/api/quiz/{quiz['id']}/retry", json={}).get_json()["quiz"]
    assert len(retry["questions"]) == wrong and retry["mode"] == "practice"


def test_timed_mode_has_a_time_limit(client):
    quiz = client.post("/api/quiz", json={"subjects": ["science"], "count": 4, "mode": "timed",
                                          "difficulty": "hard", "language": "en"}).get_json()["quiz"]
    assert quiz["time_limit"] == 4 * 90


def test_daily_goal_bonus_fires_once(client):
    register(client)
    assert client.patch("/api/me", json={"daily_goal": 0}).status_code == 400
    assert client.patch("/api/me", json={"daily_goal": 2}).get_json()["user"]["daily_goal"] == 2
    first = ask(client, "What is a fraction?")[-1]
    assert first["goal"] == {"done": 1, "goal": 2, "complete": False, "reached_now": False, "bonus_xp": 0}
    second = ask(client, "What is a decimal?")[-1]
    assert second["goal"]["reached_now"] is True and second["goal"]["bonus_xp"] == 15
    third = ask(client, "What is a percentage?")[-1]
    assert third["goal"]["reached_now"] is False
    progress = client.get("/api/progress").get_json()["progress"]
    assert progress["goal"]["done"] == 3


def test_level_up_is_reported(client):
    events = None
    for question in ["What is a fraction?", "What is a decimal?", "What is a percentage?", "What is algebra?",
                     "What is an angle?", "What is a triangle?", "What is a circle?", "What is area?",
                     "What is perimeter?", "What is an integer?", "What is division?", "What is BODMAS?",
                     "What is a ratio?", "What is a square?", "What is volume?", "What is data?", "What is a graph?"]:
        events = ask(client, question)
        if events[-1]["level_up"]:
            break
    assert events[-1]["level_up"] == 2


def test_badges_have_rarity(client):
    badges = ask(client, "What is a fraction?")[-1]["badges"]
    assert badges[0]["rarity"] == "common"


def test_teacher_can_reveal_the_saved_key(app, client):
    register(client)
    key = "nvapi-" + "k" * 40
    client.put("/api/admin/ai", json={"api_key": key})
    assert client.get("/api/admin/ai").get_json()["ai"]["saved_at"]
    assert client.get("/api/admin/ai/key").get_json()["api_key"] == key
    student = app.test_client()
    register(student, email="ravi@example.test")
    assert student.get("/api/admin/ai/key").status_code == 403


def test_translate_reports_the_detected_language(app, client, monkeypatch):
    monkeypatch.setattr(app.extensions["tatvax"].translator, "translate", lambda text, target, source: ("नमस्ते", "google"))
    data = client.post("/api/translate", json={"text": "Hello", "target": "hi"}).get_json()
    assert data == {"text": "नमस्ते", "engine": "google", "source": "en", "target": "hi"}
