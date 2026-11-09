"""AI gateway: every dojo_ai call from a notebook ends up here, on the server.

Two backends, chosen per learner:

- **ollama**: a local model served by Ollama on this machine (free, private, offline)
- **anthropic**: Claude, with the learner's own API key (stored encrypted; never sent
  into the sandbox)

The sandbox has no network, so this is the only way out, which makes it the one place
to enforce limits, keep keys safe, and report which model answered.
"""

from __future__ import annotations

import json
import os
import threading
import time
import urllib.error
import urllib.request
from collections import defaultdict, deque
from dataclasses import dataclass

import anthropic

from dojo._dojo_ai import simple_embed

OLLAMA_URL = os.environ.get("DOJO_OLLAMA_URL", "http://localhost:11434")
OLLAMA_EMBED_MODEL = os.environ.get("DOJO_OLLAMA_EMBED_MODEL", "nomic-embed-text")

# Claude models offered to learners; the first is the default.
ANTHROPIC_MODELS = ["claude-opus-5-5", "claude-sonnet-5-5", "claude-haiku-5-5"]

# Teaching-sized limits: generous for exercises, a cap on runaway loops and spend.
MAX_TOKENS_CAP = 4096
MAX_PROMPT_CHARS = 50_000
MAX_EMBED_TEXTS = 256
CALLS_PER_MINUTE = 30


class AIError(Exception):
    """A problem the learner can act on; the message is shown to them as-is."""


@dataclass
class AISettings:
    provider: str | None = None  # "ollama" | "anthropic" | None (not set up)
    model: str | None = None
    api_key: str | None = None


class RateLimiter:
    def __init__(self, per_minute: int = CALLS_PER_MINUTE):
        self.per_minute = per_minute
        self._calls: dict[int, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, user_id: int) -> None:
        now = time.monotonic()
        with self._lock:
            calls = self._calls[user_id]
            while calls and now - calls[0] > 60:
                calls.popleft()
            if len(calls) >= self.per_minute:
                raise AIError(
                    f"That's more than {self.per_minute} AI calls in a minute. "
                    "Wait a moment, and check for a loop calling the model."
                )
            calls.append(now)


class Gateway:
    def __init__(self, ollama_url: str = OLLAMA_URL):
        self.ollama_url = ollama_url.rstrip("/")
        self.limiter = RateLimiter()

    # --- status ---------------------------------------------------------------------

    def ollama_status(self) -> dict:
        try:
            tags = self._ollama("GET", "/api/tags", timeout=3)
        except AIError as e:
            return {"available": False, "models": [], "embedding": False, "error": str(e)}
        names = sorted(m["name"] for m in tags.get("models", []))
        embed_models = [n for n in names if _is_embedding_model(n)]
        return {
            "available": True,
            "models": [n for n in names if n not in embed_models],
            "embedding": any(n.split(":")[0] == OLLAMA_EMBED_MODEL for n in embed_models),
            "error": None,
        }

    def describe(self, settings: AISettings) -> dict:
        """What will answer: shown in the UI and returned by dojo_ai.backend()."""
        if settings.provider == "ollama":
            model = settings.model or (self.ollama_status()["models"] or [None])[0]
            return {"provider": "ollama", "model": model}
        if settings.provider == "anthropic":
            return {"provider": "anthropic", "model": settings.model or ANTHROPIC_MODELS[0]}
        return {"provider": None, "model": None}

    # --- calls ----------------------------------------------------------------------

    def handle(self, user_id: int, settings: AISettings, kind: str, payload: dict) -> dict:
        """Entry point for kernel ai_requests."""
        if kind == "backend":
            return self.describe(settings)
        self.limiter.check(user_id)
        if kind == "chat":
            return self.chat(settings, payload)
        if kind == "embed":
            return self.embed(settings, payload)
        raise AIError(f"Unknown AI request: {kind}")

    def chat(self, settings: AISettings, payload: dict) -> dict:
        messages = payload.get("messages") or []
        system = payload.get("system")
        size = sum(len(m.get("content", "")) for m in messages) + len(system or "")
        if size > MAX_PROMPT_CHARS:
            raise AIError(
                f"That prompt is too long for DataDojo ({size:,} characters; max {MAX_PROMPT_CHARS:,})."
            )
        max_tokens = max(1, min(int(payload.get("max_tokens") or 1024), MAX_TOKENS_CAP))
        started = time.monotonic()
        if settings.provider == "ollama":
            model, text = self._ollama_chat(settings, payload, messages, system, max_tokens)
        elif settings.provider == "anthropic":
            model, text = self._anthropic_chat(settings, payload, messages, system, max_tokens)
        else:
            raise AIError(NOT_SET_UP)
        return {
            "text": text,
            "provider": settings.provider,
            "model": model,
            "ms": round((time.monotonic() - started) * 1000),
        }

    def embed(self, settings: AISettings, payload: dict) -> dict:
        texts = payload.get("texts") or []
        if len(texts) > MAX_EMBED_TEXTS:
            raise AIError(f"Embed at most {MAX_EMBED_TEXTS} texts at a time.")
        # Ollama's embedding model when the learner uses Ollama and has it installed;
        # otherwise the built-in simple embedding (Claude has no embeddings endpoint).
        if settings.provider == "ollama" and self.ollama_status()["embedding"]:
            data = self._ollama(
                "POST", "/api/embed", {"model": OLLAMA_EMBED_MODEL, "input": texts}, timeout=120
            )
            return {
                "vectors": data["embeddings"],
                "provider": "ollama",
                "model": OLLAMA_EMBED_MODEL,
            }
        return {
            "vectors": [simple_embed(t) for t in texts],
            "provider": "builtin",
            "model": "simple_embed",
        }

    def test(self, settings: AISettings) -> dict:
        """A tiny real request, for the settings panel's Test button."""
        result = self.chat(
            settings,
            {
                "messages": [{"role": "user", "content": "Reply with just the word: ready"}],
                "max_tokens": 16,
            },
        )
        return {
            "ok": True,
            "reply": result["text"].strip()[:200],
            **{k: result[k] for k in ("provider", "model", "ms")},
        }

    # --- backends -------------------------------------------------------------------

    def _ollama_chat(self, settings, payload, messages, system, max_tokens) -> tuple[str, str]:
        model = settings.model or (self.ollama_status()["models"] or [None])[0]
        if not model:
            raise AIError("Ollama has no chat models yet. In a terminal, run: ollama pull llama3.2")
        body = {
            "model": model,
            "messages": ([{"role": "system", "content": system}] if system else []) + messages,
            "stream": False,
            "options": {"num_predict": max_tokens},
        }
        if payload.get("temperature") is not None:
            body["options"]["temperature"] = float(payload["temperature"])
        if payload.get("json"):
            body["format"] = "json"
        data = self._ollama("POST", "/api/chat", body, timeout=300)
        return model, data.get("message", {}).get("content", "")

    def _anthropic_chat(self, settings, payload, messages, system, max_tokens) -> tuple[str, str]:
        if not settings.api_key:
            raise AIError("Add your Anthropic API key in AI settings (top bar → AI).")
        model = settings.model or ANTHROPIC_MODELS[0]
        if payload.get("json"):
            extra = "Reply with valid JSON only: no prose and no code fences."
            system = f"{system}\n\n{extra}" if system else extra
        client = anthropic.Anthropic(api_key=settings.api_key, max_retries=2, timeout=120)
        kwargs: dict = {"model": model, "max_tokens": max_tokens, "messages": messages}
        if system:
            kwargs["system"] = system
        try:
            # Opt in to refusal fallbacks: if the model declines on policy grounds, the
            # API re-runs the request on a fallback model instead of returning nothing.
            response = client.beta.messages.create(
                **kwargs, betas=["server-side-fallback-2026-07-01"], fallbacks="default"
            )
        except anthropic.AuthenticationError:
            raise AIError("Anthropic rejected the API key. Check it in AI settings.") from None
        except anthropic.PermissionDeniedError:
            raise AIError("This API key isn't allowed to use that model.") from None
        except anthropic.NotFoundError:
            raise AIError(f"Anthropic doesn't recognise the model {model!r}.") from None
        except anthropic.RateLimitError:
            raise AIError(
                "Anthropic says you're sending requests too fast. Wait a moment and try again."
            ) from None
        except anthropic.BadRequestError as e:
            raise AIError(f"Anthropic couldn't process the request: {e.message}") from None
        except anthropic.APIStatusError as e:
            raise AIError(
                f"Anthropic had a problem ({e.status_code}). Try again shortly."
            ) from None
        except anthropic.APIConnectionError:
            raise AIError("Couldn't reach Anthropic. Is this computer online?") from None
        if response.stop_reason == "refusal":
            raise AIError("The model declined to answer that request.")
        text = "".join(block.text for block in response.content if block.type == "text")
        return response.model, text

    def _ollama(self, method: str, path: str, body: dict | None = None, *, timeout: float) -> dict:
        data = json.dumps(body).encode("utf-8") if body is not None else None
        request = urllib.request.Request(
            self.ollama_url + path,
            data=data,
            method=method,
            headers={"Content-Type": "application/json"} if data else {},
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.loads(response.read())
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")[:300]
            raise AIError(f"Ollama returned an error: {detail}") from None
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            raise AIError(
                f"Ollama isn't running at {self.ollama_url}. Start the Ollama app, "
                "or switch to a hosted model in AI settings."
            ) from None


NOT_SET_UP = "Choose an AI model first: top bar → AI → pick Local (Ollama) or Hosted (your key)."


def _is_embedding_model(name: str) -> bool:
    base = name.split(":")[0].lower()
    return "embed" in base or base in {
        "all-minilm",
        "bge-m3",
        "mxbai-embed-large",
        "snowflake-arctic-embed",
    }
