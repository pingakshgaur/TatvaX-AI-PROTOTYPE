import json

import pytest

from tatvax import create_app
from tatvax.security import limiter


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.delenv("TATVAX_AI", raising=False)
    monkeypatch.setenv("NVIDIA_API_KEY", "")  # no real key in tests
    monkeypatch.delenv("TATVAX_MODEL", raising=False)
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<!doctype html><div id=root></div>", encoding="utf-8")
    application = create_app({
        "INSTANCE_DIR": tmp_path,
        "DATABASE": str(tmp_path / "test.db"),
        "FRONTEND_DIST": dist,
        "TEACHER_CODE": "staff-code",
        "TESTING": True,
    })
    limiter.reset()
    # Keep tests off the network: translation always fails fast.
    from tatvax.translation import TranslationError

    def no_network(*_args, **_kwargs):
        raise TranslationError("offline in tests")

    monkeypatch.setattr(application.extensions["tatvax"].translator, "translate", no_network)
    yield application
    limiter.reset()


@pytest.fixture
def client(app):
    return app.test_client()


def stream_events(response):
    return [json.loads(line) for line in response.get_data(as_text=True).splitlines() if line.strip()]


def ask(client, message, **body):
    body = {"message": message, "mode": "subject", "subject": "mathematics", "language": "en", **body}
    response = client.post("/api/chat", json=body)
    assert response.status_code == 200, response.get_data(as_text=True)
    return stream_events(response)


def register(client, name="Asha", email="asha@example.test", password="correct-horse", **extra):
    return client.post("/api/auth/register", json={"name": name, "email": email, "password": password, **extra})
