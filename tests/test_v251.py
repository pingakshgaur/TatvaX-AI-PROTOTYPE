import json

import openai
import pytest
from conftest import register

from tatvax.ai import PROVIDERS, AIService


def test_todo_lifecycle(client):
    created = client.post("/api/todos", json={
        "title": "Revise fractions", "priority": "high", "due_date": "2026-10-20", "subject": "mathematics",
        "tags": ["exam", "exam", "maths"], "subtasks": [{"text": "Adding"}, {"text": "Dividing", "done": True}],
    })
    assert created.status_code == 201
    todo = created.get_json()["todo"]
    assert todo["tags"] == ["exam", "maths"] and len(todo["subtasks"]) == 2 and todo["done"] is False

    second = client.post("/api/todos", json={"title": "Read chapter 3"}).get_json()["todo"]
    ids = [t["id"] for t in client.get("/api/todos").get_json()["todos"]]
    assert ids[0] == second["id"]  # new tasks go to the top

    done = client.patch(f"/api/todos/{todo['id']}", json={"done": True}).get_json()["todo"]
    assert done["done"] and done["completed_at"]
    copy = client.post(f"/api/todos/{todo['id']}/duplicate", json={}).get_json()["todo"]
    assert copy["title"] == "Revise fractions (copy)"

    assert client.post("/api/todos/reorder", json={"ids": [copy["id"], second["id"]]}).status_code == 200
    assert client.post("/api/todos/bulk", json={"action": "clear_completed"}).get_json()["changed"] == 1
    assert client.delete(f"/api/todos/{second['id']}").status_code == 200
    assert [t["id"] for t in client.get("/api/todos").get_json()["todos"]] == [copy["id"]]


def test_todo_validation_and_privacy(app, client):
    assert client.post("/api/todos", json={"title": " "}).status_code == 400
    assert client.post("/api/todos", json={"title": "x", "priority": "someday"}).status_code == 400
    assert client.post("/api/todos", json={"title": "x", "due_date": "tomorrow"}).status_code == 400
    todo = client.post("/api/todos", json={"title": "Mine"}).get_json()["todo"]
    other = app.test_client()
    assert other.patch(f"/api/todos/{todo['id']}", json={"title": "Hacked"}).status_code == 404
    assert other.delete(f"/api/todos/{todo['id']}").status_code == 404


def test_guest_todos_move_to_the_account_on_login(app, client):
    register(client)
    client.post("/api/auth/logout", json={})
    device = app.test_client()
    device.post("/api/todos", json={"title": "Guest task"})
    device.post("/api/auth/login", json={"email": "asha@example.test", "password": "correct-horse"})
    assert [t["title"] for t in device.get("/api/todos").get_json()["todos"]] == ["Guest task"]


def test_assessment_history_review_retake_and_delete(client):
    quiz = client.post("/api/quiz", json={"subjects": ["science"], "count": 5, "mode": "exam", "language": "en"}).get_json()["quiz"]
    client.post(f"/api/quiz/{quiz['id']}/submit", json={"answers": [0, 1, 2, 3, 0]})
    history = client.get("/api/quizzes").get_json()["quizzes"]
    assert history[0]["id"] == quiz["id"] and history[0]["completed_at"] and history[0]["subjects"][0]["title"] == "Science"

    detail = client.get(f"/api/quiz/{quiz['id']}").get_json()["quiz"]
    assert len(detail["finished"]["results"]) == 5 and detail["mode"] == "exam"

    again = client.post(f"/api/quiz/{quiz['id']}/retake", json={}).get_json()["quiz"]
    assert again["id"] != quiz["id"] and len(again["questions"]) == 5 and again["mode"] == "exam"
    assert sorted(q["question"] for q in again["questions"]) == sorted(q["question"] for q in detail["questions"])

    assert client.delete(f"/api/quiz/{quiz['id']}").status_code == 200
    assert client.get(f"/api/quiz/{quiz['id']}").status_code == 404


def test_subjects_overview(client):
    client.post("/api/chat", json={"message": "What is a fraction?", "mode": "subject", "subject": "mathematics"}).get_data()
    subjects = {s["slug"]: s for s in client.get("/api/subjects/overview").get_json()["subjects"]}
    assert subjects["mathematics"]["chapters"] >= 10 and subjects["mathematics"]["topics"] > 20
    assert subjects["mathematics"]["questions"] == 1


def test_helpdesk_is_now_tatvai(client):
    docs = {d["slug"]: d for d in client.get("/api/library").get_json()["documents"]}
    assert docs["school-faq"]["title"] == "School Information"


# --------------------------------------------------------------------------- AI providers

def test_every_provider_is_listed_and_nvidia_stays_default(app, client):
    register(client)
    data = client.get("/api/admin/ai").get_json()
    assert data["active"] == "nvidia"
    ids = [p["id"] for p in data["providers"]]
    assert ids[0] == "nvidia" and {"gemini", "groq", "openai", "anthropic", "openrouter", "mistral", "deepseek", "ollama", "custom"} <= set(ids)


def test_switching_providers_keeps_each_key(app, client, monkeypatch):
    register(client)
    nvidia_key = "nvapi-" + "n" * 40
    client.put("/api/admin/ai", json={"provider": "nvidia", "api_key": nvidia_key})
    service = app.extensions["tatvax"].ai
    monkeypatch.setattr(service, "choose_model", lambda pid: None)  # no network in tests
    gemini = client.put("/api/admin/ai", json={"provider": "gemini", "api_key": "AIza" + "g" * 35, "activate": True}).get_json()
    assert gemini["active"] == "gemini" and gemini["ai"]["provider"] == "Google Gemini"
    assert gemini["ai"]["model"] == "gemini-flash-latest"
    assert client.get("/api/admin/ai/key?provider=nvidia").get_json()["api_key"] == nvidia_key
    assert client.get("/api/bootstrap").get_json()["app"]["ai_enabled"] is True

    custom = client.put("/api/admin/ai", json={"provider": "custom", "base_url": "ftp://nope"})
    assert custom.status_code == 400
    back = client.put("/api/admin/ai", json={"provider": "nvidia", "activate": True}).get_json()
    assert back["active"] == "nvidia" and back["ai"]["key_hint"].startswith("nvapi-")


def test_provider_settings_survive_a_restart(app, client, monkeypatch):
    register(client)
    monkeypatch.setattr(app.extensions["tatvax"].ai, "choose_model", lambda pid: None)
    client.put("/api/admin/ai", json={"provider": "groq", "api_key": "gsk_" + "q" * 40, "model": "openai/gpt-oss-20b", "activate": True})
    fresh = AIService()
    from tatvax.db import connect
    conn = connect(app.config["DATABASE"])
    fresh.load({r["key"]: r["value"] for r in conn.execute("SELECT key, value FROM settings")})
    assert fresh.active == "groq" and fresh.model == "openai/gpt-oss-20b" and fresh.available


class _FakeBadRequest(openai.BadRequestError):
    def __init__(self, message):
        self.message = message


def test_requests_adapt_to_options_a_model_rejects(monkeypatch):
    service = AIService()
    service.configure_provider("openrouter", "sk-or-" + "x" * 30, "some/model", None)
    service.set_active("openrouter")
    calls = []

    class FakeCompletions:
        def create(self, **kwargs):
            calls.append(kwargs)
            if "temperature" in kwargs:
                raise _FakeBadRequest("Unsupported parameter: 'temperature' is not supported with this model.")
            if "max_tokens" in kwargs:
                raise _FakeBadRequest("Unsupported parameter: 'max_tokens'. Use 'max_completion_tokens' instead.")

            class Choice:
                message = type("M", (), {"content": "TatvaX is connected."})

            return type("R", (), {"choices": [Choice]})

    fake = type("C", (), {"chat": type("Chat", (), {"completions": FakeCompletions()})})
    monkeypatch.setattr(service, "_openai_client", lambda pid: fake)
    assert service.complete("s", "p") == "TatvaX is connected."
    assert "max_completion_tokens" in calls[-1] and "temperature" not in calls[-1]
    assert service.states["openrouter"].dropped == {"temperature", "max_tokens"}


def test_nvidia_requests_turn_reasoning_off():
    service = AIService("nvapi-" + "z" * 40)
    kwargs = service._openai_kwargs(service.states["nvidia"], 100, 0.4)
    assert kwargs["extra_body"] == {"chat_template_kwargs": {"enable_thinking": False}}
    assert PROVIDERS["anthropic"].kind == "anthropic"


@pytest.mark.parametrize("pid", [p for p in PROVIDERS if p != "ollama"])
def test_providers_without_a_key_are_not_configured(pid, monkeypatch):
    for provider in PROVIDERS.values():
        for name in provider.env:
            monkeypatch.delenv(name, raising=False)
    assert AIService().provider_status(pid)["configured"] is False


def test_editing_a_question_rewinds_the_conversation(client):
    body = client.post("/api/chat", json={"message": "What is a fraction?", "mode": "subject", "subject": "mathematics"}).get_data(as_text=True)
    events = [json.loads(line) for line in body.splitlines() if line.strip()]
    conversation_id = events[0]["conversation_id"]
    done = events[-1]
    assert done["type"] == "done" and done["user_message_id"] < done["message_id"]
    client.post("/api/chat", json={"message": "What is a decimal?", "mode": "subject", "subject": "mathematics",
                                   "conversation_id": conversation_id}).get_data()

    rewound = client.post(f"/api/conversations/{conversation_id}/rewind", json={"message_id": done["user_message_id"]})
    assert rewound.get_json()["removed"] == 4
    assert client.get(f"/api/conversations/{conversation_id}").get_json()["messages"] == []
    assert client.post(f"/api/conversations/{conversation_id}/rewind", json={}).status_code == 400
