"""dojo_ai: talk to an AI model from CodeHoss notebooks.

    import dojo_ai
    dojo_ai.chat("Explain recursion in one sentence.")
    dojo_ai.embed(["first text", "second text"])

The same code works with whichever model you picked in CodeHoss (top bar, "AI"):
a local model through Ollama, or a hosted model with your own API key. Requests go
through the CodeHoss server, so your API key never appears in your code or notebook.

In your own projects you would use a provider's library directly, such as `ollama`
or `anthropic`; the ideas you learn here carry straight over.

While exercises are being checked, no real model is used: `chat` returns a practice
reply (or whatever the test scripts with `fake`), so checks are fast and repeatable.
"""

from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Callable

__all__ = ["chat", "embed", "simple_embed", "cosine_similarity", "backend", "fake"]

Message = dict[str, str]

# Set by the notebook kernel to reach the CodeHoss server. None means "practice mode".
_transport: Callable[[str, dict], dict] | None = None
_fake_chat: Callable[..., str] | None = None
_fake_embed: Callable[[list[str]], list[list[float]]] | None = None
calls: list[dict] = []  # practice mode records every chat call (tests inspect this)

PRACTICE_REPLY = "(Practice reply: no AI model is used while your work is being checked.)"
SIMPLE_DIMENSIONS = 256


class AIError(RuntimeError):
    """The AI model couldn't answer: not set up, unreachable, or the request was refused."""


def chat(
    prompt: str | list[Message],
    *,
    system: str | None = None,
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int = 1024,
    json: bool = False,
) -> str:
    """Send a prompt to the AI model and return its reply as text.

    `prompt` is either a string (one user message) or a list of messages like
    `[{"role": "user", "content": "Hi"}, {"role": "assistant", "content": "Hello!"}]`.
    `system` sets the model's instructions. `json=True` asks for a JSON reply.
    `temperature` (0 = focused, 1 = creative) is used by local models; hosted Claude
    models choose their own sampling and ignore it.
    """
    messages = [{"role": "user", "content": prompt}] if isinstance(prompt, str) else list(prompt)
    _check_messages(messages)
    request = {
        "messages": messages,
        "system": system,
        "model": model,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "json": json,
    }
    if _transport is None:
        calls.append(request)
        if _fake_chat is not None:
            return _fake_chat(messages, system=system, json=json)
        return '{"practice": true}' if json else PRACTICE_REPLY
    return _call("chat", request)["text"]


def embed(texts: str | list[str]) -> list[list[float]]:
    """Turn each text into a list of numbers (an embedding) that captures its meaning.

    Texts with similar meanings get similar embeddings; compare them with
    `cosine_similarity`. Uses your model's embedding service when there is one,
    otherwise `simple_embed`.
    """
    items = [texts] if isinstance(texts, str) else list(texts)
    if not all(isinstance(t, str) for t in items):
        raise TypeError("embed() takes a string or a list of strings")
    if _transport is None:
        return _fake_embed(items) if _fake_embed is not None else [simple_embed(t) for t in items]
    return _call("embed", {"texts": items})["vectors"]


def simple_embed(text: str, dimensions: int = SIMPLE_DIMENSIONS) -> list[float]:
    """A tiny built-in embedding: words are hashed into buckets and counted.

    It only notices shared words (not meaning), but it needs no model, is instant,
    and always gives the same answer.
    """
    vector = [0.0] * dimensions
    for word in re.findall(r"[a-z0-9]+", text.lower()):
        bucket = int(hashlib.md5(word.encode()).hexdigest(), 16) % dimensions
        vector[bucket] += 1.0
    norm = math.sqrt(sum(v * v for v in vector)) or 1.0
    return [v / norm for v in vector]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """How similar two embeddings are, from -1 (opposite) to 1 (same direction)."""
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return dot / norm if norm else 0.0


def backend() -> dict:
    """Which model is answering: {"provider": ..., "model": ...}."""
    if _transport is None:
        return {"provider": "practice", "model": None}
    return _call("backend", {})


def fake(chat: Callable[..., str] | None = None, embed: Callable | None = None) -> None:
    """Script practice-mode replies (used by exercise checks).

    `chat` receives `(messages, system=..., json=...)` and returns the reply text.
    """
    global _fake_chat, _fake_embed
    _fake_chat, _fake_embed = chat, embed
    calls.clear()


def _check_messages(messages: list[Message]) -> None:
    if not messages:
        raise ValueError("chat() needs at least one message")
    for message in messages:
        if not isinstance(message, dict) or message.get("role") not in ("user", "assistant"):
            raise ValueError('Each message must be a dict with role "user" or "assistant"')
        if not isinstance(message.get("content"), str):
            raise ValueError("Each message needs text content")


def _call(kind: str, payload: dict) -> dict:
    assert _transport is not None
    reply = _transport(kind, payload)
    if not reply.get("ok"):
        raise AIError(reply.get("error") or "The AI model could not answer.")
    return reply["result"]
