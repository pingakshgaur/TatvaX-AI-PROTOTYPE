"""AI tutor backend: NVIDIA's hosted models (build.nvidia.com) through their OpenAI-compatible API.

A free NVIDIA developer key is enough. Every public call raises AIUnavailable when the model
can't answer (no key, rejected key, rate limit, network), so callers fall back to the
offline study-notes engine instead of failing the student's request."""

import json
import logging
import re
import threading
from collections.abc import Iterator

import openai

log = logging.getLogger(__name__)

NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"
DEFAULT_MODEL = "google/gemma-4-31b-it"

# Shown in the teacher console. Any other model ID from build.nvidia.com can be typed in.
RECOMMENDED_MODELS = [
    {"id": "google/gemma-4-31b-it", "name": "Gemma 4 31B", "note": "Recommended. Strong in Indian languages, fast."},
    {"id": "deepseek-ai/deepseek-v4.1-flash", "name": "DeepSeek V4.1 Flash", "note": "Very good at maths and step-by-step reasoning."},
    {"id": "moonshotai/kimi-k2.6", "name": "Kimi K2.6", "note": "Large general model with detailed answers."},
    {"id": "nvidia/nemotron-3-super-120b-a12b", "name": "Nemotron 3 Super", "note": "NVIDIA's own general-purpose model."},
    {"id": "mistralai/mistral-large-2-instruct", "name": "Mistral Large 2", "note": "Reliable all-rounder."},
]


class AIUnavailable(Exception):
    """The AI model could not answer; the caller should fall back to the study notes."""

    def __init__(self, message: str, permanent: bool = False):
        super().__init__(message)
        self.permanent = permanent


class _ThinkFilter:
    """Removes <think>...</think> reasoning that some models emit before their answer,
    including when the tags are split across streamed chunks."""

    def __init__(self):
        self.inside = False
        self.pending = ""

    def feed(self, text: str) -> str:
        self.pending += text
        out = []
        while self.pending:
            if self.inside:
                end = self.pending.find("</think>")
                if end < 0:
                    self.pending = self.pending[-7:]  # keep a possible partial closing tag
                    return "".join(out)
                self.pending = self.pending[end + len("</think>"):].lstrip("\n")
                self.inside = False
            else:
                start = self.pending.find("<think>")
                if start < 0:
                    # Hold back a trailing "<" fragment that could be the start of a tag.
                    cut = self.pending.rfind("<")
                    if cut >= 0 and "<think>".startswith(self.pending[cut:]):
                        out.append(self.pending[:cut])
                        self.pending = self.pending[cut:]
                        return "".join(out)
                    out.append(self.pending)
                    self.pending = ""
                else:
                    out.append(self.pending[:start])
                    self.pending = self.pending[start + len("<think>"):]
                    self.inside = True
        return "".join(out)

    def flush(self) -> str:
        rest = "" if self.inside else self.pending
        self.pending = ""
        return rest


def strip_think(text: str) -> str:
    return re.sub(r"<think>.*?(</think>|$)", "", text, flags=re.DOTALL).strip()


def key_hint(api_key: str | None) -> str | None:
    if not api_key:
        return None
    return f"{api_key[:6]}…{api_key[-4:]}" if len(api_key) > 12 else "…"


class AIService:
    def __init__(self, env_key: str = "", model: str = DEFAULT_MODEL, allowed: bool = True):
        self.allowed = allowed  # TATVAX_AI=off turns the AI tutor off entirely
        self.env_key = env_key or ""
        self._lock = threading.Lock()
        self._client: openai.OpenAI | None = None
        self.api_key = ""
        self.env_model = model or DEFAULT_MODEL
        self.model = self.env_model
        self.source: str | None = None
        self.last_error = ""
        self.configure(None, None)

    # ------------------------------------------------------------------ configuration

    def configure(self, saved_key: str | None, saved_model: str | None) -> None:
        """Apply the key/model saved in the teacher console; an unset key falls back to the environment."""
        with self._lock:
            if saved_key:
                self.api_key, self.source = saved_key, "settings"
            elif self.env_key:
                self.api_key, self.source = self.env_key, "environment"
            else:
                self.api_key, self.source = "", None
            self.model = saved_model or self.env_model
            self._client = None
            self.last_error = ""

    @property
    def available(self) -> bool:
        return self.allowed and bool(self.api_key) and not self.last_error.startswith("rejected")

    def status(self) -> dict:
        return {
            "provider": "NVIDIA",
            "configured": bool(self.api_key),
            "available": self.available,
            "allowed": self.allowed,
            "source": self.source,
            "key_hint": key_hint(self.api_key),
            "model": self.model,
            "last_error": self.last_error.removeprefix("rejected: "),
        }

    @property
    def client(self) -> openai.OpenAI:
        with self._lock:
            if self._client is None:
                self._client = openai.OpenAI(base_url=NVIDIA_BASE_URL, api_key=self.api_key, timeout=120.0, max_retries=1)
            return self._client

    def _check(self) -> None:
        if not self.allowed:
            raise AIUnavailable("The AI tutor is turned off", permanent=True)
        if not self.api_key:
            raise AIUnavailable("No NVIDIA API key is configured", permanent=True)
        if self.last_error.startswith("rejected"):
            raise AIUnavailable(self.last_error, permanent=True)

    def _fail(self, exc: Exception) -> AIUnavailable:
        if isinstance(exc, (openai.AuthenticationError, openai.PermissionDeniedError)):
            self.last_error = "rejected: NVIDIA rejected the API key. Check it on build.nvidia.com."
            log.error("NVIDIA API key rejected: %s", exc)
            return AIUnavailable(self.last_error, permanent=True)
        if isinstance(exc, openai.NotFoundError):
            self.last_error = f"The model {self.model!r} isn't available on NVIDIA's API."
            return AIUnavailable(self.last_error)
        if isinstance(exc, openai.RateLimitError):
            self.last_error = "NVIDIA's free-tier rate limit was reached; answers used the study notes meanwhile."
            return AIUnavailable("Rate limited")
        if isinstance(exc, openai.APIStatusError):
            self.last_error = f"NVIDIA API error ({exc.status_code})."
            log.warning("NVIDIA API error %s: %s", exc.status_code, exc.message)
            return AIUnavailable(self.last_error)
        if isinstance(exc, (openai.APIConnectionError, openai.APITimeoutError)):
            self.last_error = "Couldn't reach NVIDIA's API."
            return AIUnavailable(self.last_error)
        log.exception("Unexpected AI failure")
        return AIUnavailable("Unexpected AI error")

    def _messages(self, system: str, messages: list[dict]) -> list[dict]:
        return [{"role": "system", "content": system}, *messages]

    # ------------------------------------------------------------------ calls

    def stream_reply(self, system: str, messages: list[dict], max_tokens: int = 2048) -> Iterator[tuple[str, str]]:
        """Yield ("text", chunk) events and finally ("stop", reason)."""
        self._check()
        think = _ThinkFilter()
        reason = "stop"
        try:
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=self._messages(system, messages),
                max_tokens=max_tokens,
                temperature=0.4,
                stream=True,
            )
            for chunk in stream:
                if not chunk.choices:
                    continue
                choice = chunk.choices[0]
                text = think.feed(choice.delta.content or "")
                if text:
                    yield "text", text
                if choice.finish_reason:
                    reason = choice.finish_reason
        except openai.OpenAIError as exc:
            raise self._fail(exc) from exc
        rest = think.flush()
        if rest:
            yield "text", rest
        self.last_error = ""
        yield "stop", reason

    def complete(self, system: str, prompt: str, max_tokens: int = 2048, json_mode: bool = False) -> str:
        self._check()
        kwargs = {
            "model": self.model,
            "messages": self._messages(system, [{"role": "user", "content": prompt}]),
            "max_tokens": max_tokens,
            "temperature": 0.3,
        }
        try:
            try:
                response = self.client.chat.completions.create(
                    **kwargs, **({"response_format": {"type": "json_object"}} if json_mode else {})
                )
            except openai.BadRequestError:
                if not json_mode:
                    raise
                response = self.client.chat.completions.create(**kwargs)  # model without JSON mode
        except openai.OpenAIError as exc:
            raise self._fail(exc) from exc
        self.last_error = ""
        return strip_think(response.choices[0].message.content or "")

    def generate_json(self, system: str, prompt: str, max_tokens: int = 4096) -> dict:
        text = self.complete(system, prompt, max_tokens=max_tokens, json_mode=True)
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
        start, end = text.find("{"), text.rfind("}")
        if start < 0 or end < start:
            raise AIUnavailable("The model didn't return JSON")
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError as exc:
            raise AIUnavailable("The model returned malformed JSON") from exc

    def test(self) -> str:
        """A tiny request used by the teacher console's "Test connection" button."""
        if not self.api_key:
            raise AIUnavailable("No NVIDIA API key is configured", permanent=True)
        self.last_error = ""  # allow a retry after fixing a rejected key
        return self.complete("You are a connection test.", "Reply with exactly: TatvaX is connected.", max_tokens=200)
