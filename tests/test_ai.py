"""AI gateway, settings API, and the hoss_ai learner library (no real model calls)."""

import pytest
from conftest import REPO
from fastapi.testclient import TestClient

from hoss import _hoss_ai as hoss_ai
from hoss.ai import AIError, AISettings, Gateway, RateLimiter
from hoss.api import create_app
from hoss.registry import load_content
from hoss.store import Store

# --- hoss_ai in practice mode (how exercises are graded) -----------------------------


@pytest.fixture(autouse=True)
def practice_mode():
    hoss_ai._transport = None
    hoss_ai.fake()
    yield
    hoss_ai.fake()


def test_practice_reply_and_recorded_calls():
    assert hoss_ai.chat("hello", system="be brief") == hoss_ai.PRACTICE_REPLY
    assert hoss_ai.calls[0]["messages"] == [{"role": "user", "content": "hello"}]
    assert hoss_ai.calls[0]["system"] == "be brief"


def test_scripted_fake():
    hoss_ai.fake(chat=lambda messages, **kw: f"echo: {messages[-1]['content']}")
    assert hoss_ai.chat("ping") == "echo: ping"


def test_message_validation():
    with pytest.raises(ValueError, match="role"):
        hoss_ai.chat([{"role": "system", "content": "x"}])


def test_simple_embed_is_deterministic_and_meaningful():
    cats, cats2, cars = hoss_ai.embed(["the cat sat", "a cat sat down", "engine oil change"])
    assert cats == hoss_ai.simple_embed("the cat sat")
    assert hoss_ai.cosine_similarity(cats, cats2) > hoss_ai.cosine_similarity(cats, cars)


def test_transport_errors_become_ai_errors():
    hoss_ai._transport = lambda kind, payload: {"ok": False, "error": "Ollama isn't running"}
    with pytest.raises(hoss_ai.AIError, match="Ollama"):
        hoss_ai.chat("hi")


# --- gateway -------------------------------------------------------------------------


def test_not_set_up():
    with pytest.raises(AIError, match="Choose an AI model"):
        Gateway().chat(AISettings(), {"messages": [{"role": "user", "content": "hi"}]})


def test_hosted_needs_a_key():
    with pytest.raises(AIError, match="API key"):
        Gateway().chat(
            AISettings(provider="anthropic"), {"messages": [{"role": "user", "content": "hi"}]}
        )


def test_ollama_unreachable_is_friendly():
    gateway = Gateway(ollama_url="http://127.0.0.1:9")
    assert gateway.ollama_status()["available"] is False
    with pytest.raises(AIError, match="isn't running"):
        gateway.chat(
            AISettings(provider="ollama", model="m"),
            {"messages": [{"role": "user", "content": "hi"}]},
        )


def test_prompt_size_limit():
    huge = {"messages": [{"role": "user", "content": "x" * 60_000}]}
    with pytest.raises(AIError, match="too long"):
        Gateway().chat(AISettings(provider="ollama"), huge)


def test_embed_falls_back_to_builtin_for_hosted():
    result = Gateway().embed(AISettings(provider="anthropic", api_key="k"), {"texts": ["a b"]})
    assert result["provider"] == "builtin"
    assert result["vectors"][0] == hoss_ai.simple_embed("a b")


def test_rate_limiter():
    limiter = RateLimiter(per_minute=2)
    limiter.check(1)
    limiter.check(1)
    with pytest.raises(AIError, match="2 AI calls"):
        limiter.check(1)
    limiter.check(2)  # per user


# --- settings API --------------------------------------------------------------------


class FakeGateway(Gateway):
    def __init__(self):
        super().__init__(ollama_url="http://127.0.0.1:9")

    def ollama_status(self):
        return {"available": True, "models": ["qwen2.5:7b"], "embedding": True, "error": None}

    def chat(self, settings, payload):
        if settings.provider is None:
            raise AIError("Choose an AI model first")
        return {
            "text": "ready",
            "provider": settings.provider,
            "model": settings.model or "m",
            "ms": 1,
        }


@pytest.fixture
def client(tmp_path):
    app = create_app(
        load_content(REPO / "content"), store=Store(tmp_path / "db"), gateway=FakeGateway()
    )
    with TestClient(app) as client:
        client.post("/api/auth/register", json={"username": "ada", "password": "password1"})
        yield client


def test_status_starts_unset(client):
    status = client.get("/api/ai/status").json()
    assert status["provider"] is None and status["current"] is None
    assert status["ollama"]["models"] == ["qwen2.5:7b"]
    assert status["anthropic"]["configured"] is False
    assert status["anthropic"]["models"][0] == "claude-opus-5-5"


def test_choose_ollama(client):
    status = client.put(
        "/api/ai/settings", json={"provider": "ollama", "model": "qwen2.5:7b"}
    ).json()
    assert status["current"] == {"provider": "ollama", "model": "qwen2.5:7b"}
    assert status["embeddings"] == "ollama"
    assert client.post("/api/ai/test").json()["ok"] is True


def test_hosted_key_is_never_returned(client):
    assert client.put("/api/ai/settings", json={"provider": "anthropic"}).status_code == 400
    status = client.put(
        "/api/ai/settings", json={"provider": "anthropic", "api_key": "sk-ant-secret-1234"}
    ).json()
    assert status["anthropic"] == {
        "configured": True,
        "key_hint": "…1234",
        "models": status["anthropic"]["models"],
        "selected_model": None,
    }
    assert "sk-ant-secret" not in client.get("/api/ai/status").text
    # Switching to Ollama keeps the key for later; clearing removes it.
    client.put("/api/ai/settings", json={"provider": "ollama"})
    assert client.get("/api/ai/status").json()["anthropic"]["configured"] is True
    client.put("/api/ai/settings", json={"provider": "ollama", "clear_key": True})
    assert client.get("/api/ai/status").json()["anthropic"]["configured"] is False


def test_unknown_claude_model_rejected(client):
    response = client.put(
        "/api/ai/settings", json={"provider": "anthropic", "api_key": "k", "model": "gpt-9"}
    )
    assert response.status_code == 400


def test_key_is_encrypted_at_rest(tmp_path):
    import sqlite3

    store = Store(tmp_path / "db")
    user = store.register("ada", "password1")
    store.save_ai_settings(user, provider="anthropic", model=None, api_key="sk-ant-plaintext")
    raw = (
        sqlite3.connect(tmp_path / "db")
        .execute("SELECT api_key_encrypted FROM ai_settings")
        .fetchone()[0]
    )
    assert b"sk-ant-plaintext" not in raw
    assert store.ai_settings(user).api_key == "sk-ant-plaintext"
