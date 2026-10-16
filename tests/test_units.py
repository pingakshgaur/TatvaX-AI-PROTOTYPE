from datetime import date, timedelta

from conftest import ask

from tatvax import gamification, languages, speech, translation
from tatvax.ai import AIService, AIUnavailable, _ThinkFilter, strip_think
from tatvax.db import connect
from tatvax.knowledge import split_sections, tokenize


def test_language_detection():
    assert languages.detect_language("What is gravity?") == "en"
    assert languages.detect_language("गुरुत्वाकर्षण क्या है?") == "hi"
    assert languages.detect_language("माझे नाव काय आहे?") == "mr"
    assert languages.detect_language("জল চক্ৰ কি?") == "as"
    assert languages.detect_language("জল চক্র কী?") == "bn"
    assert languages.detect_language("நீர் சுழற்சி என்ன?") == "ta"
    assert languages.detect_language("پانی کا چکر کیا ہے؟") == "ur"
    assert languages.detect_language("12 + 7") == "en"


def test_tokenizer_drops_stopwords_and_stems_plurals():
    assert tokenize("What are the rights of citizens?") == ["right", "citizen"]
    assert tokenize("fees") == tokenize("fee")


def test_split_sections_uses_chapters_and_topics():
    body = "## Chapter 1: Numbers\n\n**Integers**\nWhole numbers and negatives.\n\n**Fractions**\nParts of a whole thing."
    sections = split_sections("maths", "Maths", body)
    assert [s.heading for s in sections] == ["Chapter 1: Numbers › Integers", "Chapter 1: Numbers › Fractions"]


def test_speech_cleaning_keeps_indic_vowel_signs():
    # v1 stripped matras (combining vowel signs), mangling every Indic sentence.
    assert speech.clean_for_speech("**नमस्ते**, आप कैसे हैं?") == "नमस्ते , आप कैसे हैं?"
    assert speech.clean_for_speech("Area = $\\frac{1}{2} \\times b$") == "Area = 1 / 2 × b"


def test_level_curve():
    assert gamification.level_info(0)["level"] == 1
    assert gamification.level_info(99)["level"] == 1
    assert gamification.level_info(100)["level"] == 2
    assert gamification.level_info(300)["level"] == 3
    assert gamification.level_info(150)["progress"] == 0.25


def test_streaks(app, client, monkeypatch):
    ask(client, "What is a fraction?")
    conn = connect(app.config["DATABASE"])
    user_id = conn.execute("SELECT id FROM users").fetchone()[0]
    today = date.today()
    for offset in (1, 2, 5):
        conn.execute("INSERT OR IGNORE INTO activity (user_id, day, questions) VALUES (?, ?, 1)",
                      (user_id, (today - timedelta(days=offset)).isoformat()))
    conn.commit()
    monkeypatch.setattr(gamification, "today", lambda: today.isoformat())
    assert gamification.streaks(conn, user_id) == {"current": 3, "best": 3}
    conn.close()


def test_google_translation_batches_lines(monkeypatch):
    calls = []

    class FakeResponse:
        def __init__(self, text):
            self.text = text

        def raise_for_status(self):
            pass

        def json(self):
            return [[[self.text.upper(), self.text]]]

    def fake_post(_url, params, data, timeout):
        calls.append(data["q"])
        return FakeResponse(data["q"])

    monkeypatch.setattr(translation.requests, "post", fake_post)
    translation._google.cache_clear()
    out = translation._google("## Heading\nline one\n\n- item", "en", "hi")
    assert out == "## HEADING\nLINE ONE\n\n- ITEM"
    assert len(calls) == 1  # one request for the whole answer, not one per line


class FakeAI:
    """Stands in for AIService so the AI path can be tested without network access."""

    def __init__(self, chunks=None, fail=False):
        self.available = True
        self.chunks = chunks or ["Hello ", "student!"]
        self.fail = fail
        self.calls = []

    def stream_reply(self, system, messages, max_tokens=2048):
        self.calls.append({"system": system, "messages": messages})
        if self.fail:
            raise AIUnavailable("rate limited")
        for chunk in self.chunks:
            yield "text", chunk
        yield "stop", "stop"


def test_tutor_streams_ai_answers_grounded_in_the_notes(app, client):
    fake = FakeAI()
    app.extensions["tatvax"].tutor.ai = fake
    events = ask(client, "Explain BODMAS", language="hi")
    assert [e["type"] for e in events] == ["start", "delta", "delta", "done"]
    assert events[-1]["engine"] == "ai"

    call = fake.calls[0]
    final_user = call["messages"][-1]["content"]
    # Only the best-matching sections are sent, which keeps prompts short and replies fast.
    assert "<library>" not in call["system"]
    assert "<relevant_notes>" in final_user and "BODMAS" in final_user
    assert len(final_user) < 6000
    assert "Reply language: Hindi" in final_user and final_user.endswith("Explain BODMAS")

    # Follow-ups replay the earlier exchange as history.
    ask(client, "Give an example", conversation_id=events[0]["conversation_id"])
    history = fake.calls[1]["messages"]
    assert history[0]["content"] == final_user
    assert history[1] == {"role": "assistant", "content": "Hello student!"}


def test_all_subjects_sends_only_relevant_sections(app, client):
    fake = FakeAI()
    app.extensions["tatvax"].tutor.ai = fake
    ask(client, "What is photosynthesis?", subject="all")
    call = fake.calls[0]
    assert "<library>" not in call["system"]
    assert "<relevant_notes>" in call["messages"][-1]["content"]
    assert "Photosynthesis" in call["messages"][-1]["content"]


def test_tutor_falls_back_to_notes_when_the_ai_is_unavailable(app, client):
    app.extensions["tatvax"].tutor.ai = FakeAI(fail=True)
    events = ask(client, "Explain the BODMAS rule")
    assert events[-1]["engine"] == "library"
    assert "BODMAS" in events[1]["text"]
    assert "AI tutor is unavailable" in events[1]["text"]


def test_think_filter_hides_reasoning_across_chunks():
    f = _ThinkFilter()
    chunks = ["Hi <thi", "nk>secret plan", " more</th", "ink>\nAnswer", " is 4 <b"]
    out = "".join(f.feed(c) for c in chunks) + f.flush()
    assert out == "Hi Answer is 4 <b"
    assert strip_think("<think>x</think>Done") == "Done"


def test_generate_json_tolerates_fenced_output(monkeypatch):
    service = AIService("nvapi-" + "x" * 30)
    monkeypatch.setattr(service, "complete", lambda *a, **k: '```json\n{"questions": []}\n```')
    assert service.generate_json("s", "p") == {"questions": []}
    monkeypatch.setattr(service, "complete", lambda *a, **k: "Sorry, I can't.")
    try:
        service.generate_json("s", "p")
        raise AssertionError("expected AIUnavailable")
    except AIUnavailable:
        pass


def test_ai_service_key_sources():
    service = AIService(env_key="", model="")
    assert not service.available and service.model == "nvidia/nemotron-3-super-120b-a12b"
    service = AIService(env_key="nvapi-env-key-0000000000000")
    assert service.available and service.source == "environment"
    service.configure("nvapi-saved-key-11111111111", "deepseek-ai/deepseek-v4.1-flash")
    assert service.source == "settings" and service.model == "deepseek-ai/deepseek-v4.1-flash"
    assert service.status()["key_hint"] == "nvapi-…1111"
    service.configure(None, None)  # removing the saved key falls back to the environment
    assert service.source == "environment" and service.model == "nvidia/nemotron-3-super-120b-a12b"
    assert not AIService(env_key="nvapi-env-key-0000000000000", allowed=False).available
