from conftest import ask, register


def test_bootstrap_lists_languages_and_subjects(client):
    data = client.get("/api/bootstrap").get_json()
    assert len(data["app"]["languages"]) == 13
    assert {s["slug"] for s in data["app"]["subjects"]} == {"mathematics", "science", "english", "social-studies"}
    assert data["app"]["helpdesk"]["slug"] == "school-faq"
    assert data["app"]["ai_enabled"] is False
    assert data["user"] is None  # visiting doesn't create a profile


def test_chat_streams_an_answer_from_the_notes(client):
    events = ask(client, "Explain the BODMAS rule")
    assert [e["type"] for e in events] == ["start", "replace", "done"]
    assert "BODMAS" in events[1]["text"]
    done = events[-1]
    assert done["engine"] == "library"
    assert done["xp_gained"] == 15  # daily bonus + question
    assert done["badges"][0]["id"] == "first_question"
    assert done["sources"]


def test_follow_up_keeps_the_conversation(client):
    first = ask(client, "What is a fraction?")
    conversation_id = first[0]["conversation_id"]
    second = ask(client, "And decimals?", conversation_id=conversation_id)
    assert second[0]["conversation_id"] == conversation_id
    detail = client.get(f"/api/conversations/{conversation_id}").get_json()
    assert [m["role"] for m in detail["messages"]] == ["user", "assistant", "user", "assistant"]


def test_helpdesk_mode_answers_from_school_information(client):
    events = ask(client, "What documents are needed for admission?", mode="helpdesk", subject=None)
    assert "School Help Desk" in events[1]["text"]


def test_chat_validation(client):
    assert client.post("/api/chat", json={"message": "  "}).status_code == 400
    assert client.post("/api/chat", json={"message": "x" * 2001}).status_code == 400
    assert client.post("/api/chat", json={"message": "hi", "subject": "astrology"}).status_code == 400
    assert client.post("/api/chat", json={"message": "hi", "conversation_id": 999}).status_code == 404


def test_writes_must_be_json(client):
    # A cross-site form post can't set a JSON content type, so this blocks CSRF.
    assert client.post("/api/chat", data={"message": "hi"}).status_code == 415
    assert client.post("/api/auth/logout", data="").status_code == 415


def test_conversations_are_private(app, client):
    conversation_id = ask(client, "What is a fraction?")[0]["conversation_id"]
    other = app.test_client()
    assert other.get(f"/api/conversations/{conversation_id}").status_code == 404
    assert other.delete(f"/api/conversations/{conversation_id}").status_code == 404
    assert client.delete(f"/api/conversations/{conversation_id}").status_code == 200
    assert client.get("/api/conversations").get_json()["conversations"] == []


def test_chat_rate_limit(app, client):
    app.config["CHAT_RATE_LIMIT"] = 2
    ask(client, "What is a fraction?")
    ask(client, "What is a decimal?")
    assert client.post("/api/chat", json={"message": "again"}).status_code == 429


def test_quiz_flow_awards_xp_and_badges(client):
    quiz = client.post("/api/quiz", json={"subject": "science", "count": 5, "language": "en"}).get_json()["quiz"]
    assert quiz["engine"] == "library"
    assert len(quiz["questions"]) == 5
    assert "answer_index" not in quiz["questions"][0]  # answers stay on the server

    result = None
    for index in range(5):
        result = client.post(f"/api/quiz/{quiz['id']}/answer", json={"index": index, "choice": 0}).get_json()
        assert set(result) >= {"correct", "answer_index", "explanation"}
    finished = result["finished"]
    assert finished["total"] == 5
    assert finished["xp_gained"] >= 20
    assert any(b["id"] == "first_quiz" for b in finished["badges"])

    again = client.post(f"/api/quiz/{quiz['id']}/answer", json={"index": 0, "choice": 1})
    assert again.status_code == 400


def test_quiz_rejects_unknown_subject(client):
    assert client.post("/api/quiz", json={"subject": "nope"}).status_code == 400


def test_progress_and_leaderboard(client):
    assert client.get("/api/progress").get_json()["progress"] is None
    ask(client, "What is a fraction?")
    progress = client.get("/api/progress").get_json()["progress"]
    assert progress["xp"] == 15
    assert progress["streak"]["current"] == 1
    assert len(progress["activity"]) == 14
    assert progress["activity"][-1]["questions"] == 1
    # Guests are never on the leaderboard.
    assert client.get("/api/leaderboard").get_json()["leaderboard"] == []


def test_library_and_search(client):
    docs = client.get("/api/library").get_json()["documents"]
    assert len(docs) == 5
    doc = client.get("/api/library/science").get_json()["document"]
    assert "Chapter" in doc["body"]
    results = client.get("/api/search?q=photosynthesis").get_json()["results"]
    assert results and results[0]["slug"] == "science"


def test_feedback_is_stored_privately(client):
    assert client.post("/api/feedback", json={"message": "Great app", "rating": 5}).status_code == 201
    assert client.post("/api/feedback", json={"message": "x", "rating": 9}).status_code == 400
    # Feedback is only visible to teachers.
    assert client.get("/api/admin/feedback").status_code == 401


def test_tts_rejects_unsupported_languages(client):
    response = client.post("/api/tts", json={"text": "ନମସ୍କାର", "language": "or"})
    assert response.status_code == 422


def test_spa_routes_serve_the_react_app(client):
    for path in ("/", "/learn/mathematics", "/teacher/content/new"):
        response = client.get(path)
        assert response.status_code == 200
        assert b'id=root' in response.data
    assert client.get("/api/does-not-exist").status_code == 404


def test_security_headers(client):
    response = client.get("/")
    assert "script-src 'self'" in response.headers["Content-Security-Policy"]
    assert response.headers["X-Content-Type-Options"] == "nosniff"
