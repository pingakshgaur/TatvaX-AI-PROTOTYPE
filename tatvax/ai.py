"""AI tutor backend with a choice of providers.

NVIDIA (the default, free) and most other providers are reached through their OpenAI-compatible
APIs; Claude goes through Anthropic's own SDK. Every public call raises AIUnavailable when the
model can't answer (no key, rejected key, rate limit, network), so callers fall back to the
offline study-notes engine instead of failing the student's request."""

import dataclasses
import json
import logging
import os
import re
import threading
from collections.abc import Iterator
from dataclasses import dataclass, field

import openai

log = logging.getLogger(__name__)

NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"
DEFAULT_MODEL = "nvidia/nemotron-3-super-120b-a12b"

# Shown in the teacher console for NVIDIA. Any other model ID from build.nvidia.com can be typed in.
RECOMMENDED_MODELS = [
    {"id": "nvidia/nemotron-3-super-120b-a12b", "name": "Nemotron 3 Super", "note": "Recommended. Fast replies (about a second to the first word) and strong reasoning."},
    {"id": "deepseek-ai/deepseek-v4.1-flash", "name": "DeepSeek V4.1 Flash", "note": "Very good at maths and step-by-step reasoning."},
    {"id": "moonshotai/kimi-k2.6", "name": "Kimi K2.6", "note": "Large general model with detailed answers."},
    {"id": "mistralai/mistral-large-2-instruct", "name": "Mistral Large 2", "note": "Reliable all-rounder."},
    {"id": "google/gemma-4-31b-it", "name": "Gemma 4 31B", "note": "Strong in Indian languages, but often slow on NVIDIA's free tier."},
]


@dataclass(frozen=True)
class Provider:
    id: str
    name: str
    kind: str                       # "openai" (OpenAI-compatible API) or "anthropic"
    base_url: str = ""
    env: tuple = ()
    key_prefix: str = ""
    key_url: str = ""
    default_model: str = ""
    models: tuple = ()               # (id, label, note)
    free: str = ""                   # short note about free usage
    needs_key: bool = True
    needs_base_url: bool = False
    extra_body: dict = field(default_factory=dict)
    request_options: dict = field(default_factory=dict)
    vision_model: str = ""           # used for questions with a photo when the chosen model is text-only


PROVIDERS: dict[str, Provider] = {p.id: p for p in [
    Provider("nvidia", "NVIDIA", "openai", NVIDIA_BASE_URL, ("NVIDIA_API_KEY",), "nvapi-", "https://build.nvidia.com/settings/api-keys",
             DEFAULT_MODEL, tuple((m["id"], m["name"], m["note"]) for m in RECOMMENDED_MODELS),
             "Free developer key, about 40 requests a minute.",
             # Answer directly instead of reasoning first: replies start about twice as fast.
             extra_body={"chat_template_kwargs": {"enable_thinking": False}},
             vision_model="nvidia/nemotron-3.5-super-vl-120b-a12b"),
    Provider("gemini", "Google Gemini", "openai", "https://generativelanguage.googleapis.com/v1beta/openai/",
             ("GEMINI_API_KEY", "GOOGLE_API_KEY"), "AIza", "https://aistudio.google.com/apikey", "gemini-flash-latest",
             (("gemini-flash-latest", "Gemini Flash (latest)", "Fast, free tier available."),
              ("gemini-flash-lite-latest", "Gemini Flash-Lite (latest)", "Fastest and lightest."),
              ("gemini-pro-latest", "Gemini Pro (latest)", "Most capable Gemini model.")),
             "Free tier with daily limits."),
    Provider("groq", "Groq", "openai", "https://api.groq.com/openai/v1", ("GROQ_API_KEY",), "gsk_", "https://console.groq.com/keys",
             "openai/gpt-oss-120b",
             (("openai/gpt-oss-120b", "GPT-OSS 120B", "Very fast, strong all-rounder."),
              ("openai/gpt-oss-20b", "GPT-OSS 20B", "Extremely fast and light.")),
             "Free tier; known for very fast replies.",
             request_options={"reasoning_effort": "low"}),
    Provider("openrouter", "OpenRouter", "openai", "https://openrouter.ai/api/v1", ("OPENROUTER_API_KEY",), "sk-or-",
             "https://openrouter.ai/settings/keys", "openrouter/auto",
             (("openrouter/auto", "Auto router", "OpenRouter picks a suitable model for each question."),),
             "One key for hundreds of models, including free ones."),
    Provider("openai", "OpenAI", "openai", "https://api.openai.com/v1", ("OPENAI_API_KEY",), "sk-",
             "https://platform.openai.com/api-keys", "gpt-5.5",
             (("gpt-5.5", "GPT-5.5", "OpenAI's recommended production model."),
              ("gpt-5.6-luna", "GPT-5.6 Luna", "Newest, fast tier.")),
             "Paid; billed per token.",
             request_options={"reasoning_effort": "low"}),
    Provider("anthropic", "Anthropic Claude", "anthropic", "", ("ANTHROPIC_API_KEY",), "sk-ant-",
             "https://console.anthropic.com/settings/keys", "claude-opus-5-5",
             (("claude-opus-5-5", "Claude Opus 5.5", "Anthropic's most capable widely used model."),
              ("claude-sonnet-5-5", "Claude Sonnet 5.5", "Fast and capable."),
              ("claude-haiku-5-5", "Claude Haiku 5.5", "Fastest and lowest cost.")),
             "Paid; billed per token."),
    Provider("mistral", "Mistral AI", "openai", "https://api.mistral.ai/v1", ("MISTRAL_API_KEY",), "",
             "https://console.mistral.ai/api-keys", "mistral-large-latest",
             (("mistral-large-latest", "Mistral Large", "Most capable Mistral model."),
              ("mistral-medium-latest", "Mistral Medium", "Balanced."),
              ("mistral-small-latest", "Mistral Small", "Fast and light.")),
             "Free experiment tier available."),
    Provider("deepseek", "DeepSeek", "openai", "https://api.deepseek.com", ("DEEPSEEK_API_KEY",), "sk-",
             "https://platform.deepseek.com/api_keys", "deepseek-chat",
             (("deepseek-chat", "DeepSeek Chat", "Fast general model."),
              ("deepseek-reasoner", "DeepSeek Reasoner", "Thinks before answering; slower.")),
             "Low-cost paid API."),
    Provider("together", "Together AI", "openai", "https://api.together.xyz/v1", ("TOGETHER_API_KEY",), "",
             "https://api.together.ai/settings/api-keys", "", (), "Many open models; free credits for new accounts."),
    Provider("xai", "xAI Grok", "openai", "https://api.x.ai/v1", ("XAI_API_KEY",), "xai-",
             "https://console.x.ai", "", (), "Paid; billed per token."),
    Provider("ollama", "Ollama (on this computer)", "openai", "http://localhost:11434/v1", (), "", "https://ollama.com/download",
             "", (), "Free and private: runs models on your own computer.", needs_key=False),
    Provider("custom", "Custom (OpenAI-compatible)", "openai", "", ("TATVAX_CUSTOM_API_KEY",), "", "", "", (),
             "Any server that speaks the OpenAI chat API.", needs_base_url=True),
]}

# Models in a provider's list that can't chat (embeddings, speech, images, moderation...).
_NOT_CHAT = re.compile(r"embed|whisper|tts|speech|audio|image|dall-e|vision-only|moderation|rerank|guard|transcri|realtime|clip|ocr", re.I)


# Statuses with which providers turn down a picture they can't read (or a vision model that doesn't exist).
IMAGE_REJECTED = {400, 404, 415, 422}

_LOOKS_VISUAL = re.compile(r"(vision|[-_.]vl|-vl-|maverick|scout|multimodal|omni)", re.I)


class AIUnavailable(Exception):
    """The AI model could not answer; the caller should fall back to the study notes."""

    def __init__(self, message: str, permanent: bool = False, status: int | None = None):
        super().__init__(message)
        self.permanent = permanent
        self.status = status  # HTTP status from the provider, when there was one


# Settings rows that configure the AI providers (see AIService.load).
AI_SETTING_PREFIXES = ("nvidia_api_key", "ai_model", "ai_provider", "api_key:", "base_url:")


def settings_signature(settings: dict) -> tuple:
    return tuple(sorted((k, v) for k, v in settings.items() if k.startswith(AI_SETTING_PREFIXES)))


class ImagesUnsupported(AIUnavailable):
    """The model rejected a question that included a picture."""


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


@dataclass
class ProviderState:
    """The key, model and endpoint in use for one provider."""
    provider: Provider
    api_key: str = ""
    model: str = ""
    base_url: str = ""
    source: str | None = None        # "settings" | "environment" | None
    last_error: str = ""
    # Request options a model rejected once ("max_tokens", "temperature", ...); not sent again.
    dropped: set = field(default_factory=set)

    @property
    def configured(self) -> bool:
        has_key = bool(self.api_key) or not self.provider.needs_key
        has_url = bool(self.base_url) or not self.provider.needs_base_url
        return has_key and has_url and bool(self.model or self.provider.default_model)

    @property
    def rejected(self) -> bool:
        return self.last_error.startswith("rejected")


class AIService:
    def __init__(self, env_key: str = "", model: str = DEFAULT_MODEL, allowed: bool = True):
        self.allowed = allowed  # TATVAX_AI=off turns the AI tutor off entirely
        self._lock = threading.Lock()
        self._clients: dict = {}
        self.states: dict[str, ProviderState] = {pid: ProviderState(p) for pid, p in PROVIDERS.items()}
        self.env_keys = {pid: next((os.environ.get(v, "") for v in p.env if os.environ.get(v)), "")
                         for pid, p in PROVIDERS.items()}
        self.env_keys["nvidia"] = env_key or ""   # NVIDIA's key comes from app config (NVIDIA_API_KEY)
        self.env_model = model or DEFAULT_MODEL
        self.active = "nvidia"
        self._signature: tuple | None = None
        self.configure(None, None)
        for pid in PROVIDERS:
            if pid != "nvidia":
                self.configure_provider(pid, None, None, None)

    # ------------------------------------------------------------------ configuration

    def configure(self, saved_key: str | None, saved_model: str | None) -> None:
        """NVIDIA: apply the key/model saved in the teacher console; an unset key falls back to the environment."""
        with self._lock:
            state = self.states["nvidia"]
            if saved_key:
                state.api_key, state.source = saved_key, "settings"
            elif self.env_keys["nvidia"]:
                state.api_key, state.source = self.env_keys["nvidia"], "environment"
            else:
                state.api_key, state.source = "", None
            state.model = saved_model or self.env_model
            state.base_url = NVIDIA_BASE_URL
            state.last_error = ""
            state.dropped = set()
            self._clients.pop("nvidia", None)

    def configure_provider(self, pid: str, saved_key: str | None, saved_model: str | None, saved_base_url: str | None) -> None:
        if pid == "nvidia":
            self.configure(saved_key, saved_model)
            return
        provider = PROVIDERS[pid]
        with self._lock:
            state = self.states[pid]
            if saved_key:
                state.api_key, state.source = saved_key, "settings"
            elif self.env_keys.get(pid):
                state.api_key, state.source = self.env_keys[pid], "environment"
            else:
                state.api_key, state.source = "", None
            state.model = saved_model or provider.default_model
            state.base_url = (saved_base_url or provider.base_url).rstrip("/")
            state.last_error = ""
            state.dropped = set()
            self._clients.pop(pid, None)

    def load(self, settings: dict) -> None:
        """Apply every provider's saved settings (a dict of the settings table)."""
        self.configure(settings.get("nvidia_api_key"), settings.get("ai_model"))
        for pid in PROVIDERS:
            if pid != "nvidia":
                self.configure_provider(pid, settings.get(f"api_key:{pid}"), settings.get(f"ai_model:{pid}"),
                                        settings.get(f"base_url:{pid}"))
        active = settings.get("ai_provider")
        self.active = active if active in PROVIDERS else "nvidia"
        self._signature = settings_signature(settings)

    def sync(self, settings: dict) -> bool:
        """Reload when the saved settings differ from the ones in use (another server process may
        have saved new ones). Returns True if anything was reloaded."""
        if settings_signature(settings) == self._signature:
            return False
        self.load(settings)
        return True

    def set_active(self, pid: str) -> None:
        if pid not in PROVIDERS:
            raise ValueError("Unknown provider")
        self.active = pid

    # Back-compatible views of the active provider.
    @property
    def state(self) -> ProviderState:
        return self.states[self.active]

    @property
    def api_key(self) -> str:
        return self.state.api_key

    @property
    def model(self) -> str:
        return self.state.model or self.state.provider.default_model

    @property
    def source(self) -> str | None:
        return self.state.source

    @property
    def last_error(self) -> str:
        return self.state.last_error

    @last_error.setter
    def last_error(self, value: str) -> None:
        self.state.last_error = value

    @property
    def available(self) -> bool:
        return self.allowed and self.state.configured and not self.state.rejected

    def provider_status(self, pid: str) -> dict:
        state, provider = self.states[pid], PROVIDERS[pid]
        return {
            "id": pid,
            "name": provider.name,
            "configured": state.configured,
            "available": self.allowed and state.configured and not state.rejected,
            "active": pid == self.active,
            "source": state.source,
            "key_hint": key_hint(state.api_key),
            "model": state.model or provider.default_model,
            "base_url": state.base_url,
            "last_error": state.last_error.removeprefix("rejected: "),
            "needs_key": provider.needs_key,
            "needs_base_url": provider.needs_base_url,
            "key_prefix": provider.key_prefix,
            "key_url": provider.key_url,
            "free": provider.free,
            "models": [{"id": m, "name": n, "note": note} for m, n, note in provider.models],
        }

    def status(self) -> dict:
        state = self.state
        return {
            "provider": state.provider.name,
            "provider_id": self.active,
            "configured": state.configured,
            "available": self.available,
            "allowed": self.allowed,
            "source": state.source,
            "key_hint": key_hint(state.api_key),
            "model": self.model,
            "last_error": state.last_error.removeprefix("rejected: "),
        }

    # ------------------------------------------------------------------ clients

    def _openai_client(self, pid: str) -> openai.OpenAI:
        state = self.states[pid]
        with self._lock:
            client = self._clients.get(pid)
            if client is None:
                client = openai.OpenAI(base_url=state.base_url, api_key=state.api_key or "not-needed",
                                       timeout=120.0, max_retries=2)
                self._clients[pid] = client
            return client

    def _anthropic_client(self):
        import anthropic

        with self._lock:
            client = self._clients.get("anthropic")
            if client is None:
                client = anthropic.Anthropic(api_key=self.states["anthropic"].api_key, timeout=180.0, max_retries=2)
                self._clients["anthropic"] = client
            return client

    def _check(self, pid: str) -> ProviderState:
        state = self.states[pid]
        if not self.allowed:
            raise AIUnavailable("The AI tutor is turned off", permanent=True)
        if not state.configured:
            raise AIUnavailable(f"{state.provider.name} isn't set up yet", permanent=True)
        if state.rejected:
            raise AIUnavailable(state.last_error, permanent=True)
        return state

    # ------------------------------------------------------------------ errors

    def _fail(self, state: ProviderState, exc: Exception) -> AIUnavailable:
        name = state.provider.name
        status = getattr(exc, "status_code", None)
        message = getattr(exc, "message", None) or str(exc)
        if status in (401, 403):
            state.last_error = f"rejected: {name} rejected the API key. Check it and save it again."
            log.error("%s API key rejected: %s", name, message)
            return AIUnavailable(state.last_error, permanent=True, status=status)
        if status == 404:
            state.last_error = f"The model {state.model!r} isn't available on {name}. Choose another model."
            return AIUnavailable(state.last_error, status=status)
        if status == 429:
            state.last_error = f"{name}'s rate limit was reached; answers used the study notes meanwhile."
            return AIUnavailable("Rate limited", status=status)
        if status == 402:
            state.last_error = f"{name} says the account has no credit left."
            return AIUnavailable(state.last_error, status=status)
        if status:
            state.last_error = f"{name} API error ({status}): {message[:160]}"
            log.warning("%s API error %s: %s", name, status, message)
            return AIUnavailable(state.last_error, status=status)
        if "connect" in type(exc).__name__.lower() or "timeout" in type(exc).__name__.lower():
            hint = " Is Ollama running?" if state.provider.id == "ollama" else ""
            state.last_error = f"Couldn't reach {name}.{hint}"
            return AIUnavailable(state.last_error)
        log.exception("Unexpected AI failure")
        return AIUnavailable("Unexpected AI error")

    # ------------------------------------------------------------------ OpenAI-compatible calls

    def _openai_kwargs(self, state: ProviderState, max_tokens: int, temperature: float) -> dict:
        kwargs: dict = {"model": state.model or state.provider.default_model}
        if state.provider.id == "openai" or "max_tokens" in state.dropped:
            kwargs["max_completion_tokens"] = max_tokens
        else:
            kwargs["max_tokens"] = max_tokens
        if state.provider.id != "openai" and "temperature" not in state.dropped:
            kwargs["temperature"] = temperature
        for key, value in state.provider.request_options.items():
            if key not in state.dropped:
                kwargs[key] = value
        if state.provider.extra_body and "extra_body" not in state.dropped:
            kwargs["extra_body"] = state.provider.extra_body
        return kwargs

    def _adapt(self, state: ProviderState, exc: openai.BadRequestError, kwargs: dict) -> bool:
        """After a 400, drop or rename the option the model rejected. Returns True to retry."""
        text = (getattr(exc, "message", "") or str(exc)).lower()
        for option, hints in (
            ("max_tokens", ("max_tokens", "max_completion_tokens")),
            ("temperature", ("temperature",)),
            ("response_format", ("response_format", "json_object", "json mode")),
            ("reasoning_effort", ("reasoning_effort", "reasoning effort")),
            ("extra_body", ("chat_template_kwargs", "enable_thinking", "extra")),
        ):
            if option in state.dropped or not any(h in text for h in hints):
                continue
            if option == "max_tokens" and "max_tokens" in kwargs:
                kwargs["max_completion_tokens"] = kwargs.pop("max_tokens")
            elif option == "max_tokens":
                continue
            elif option == "extra_body":
                kwargs.pop("extra_body", None)
            else:
                kwargs.pop(option, None)
            state.dropped.add(option)
            log.info("%s/%s: retrying without %s", state.provider.id, kwargs.get("model"), option)
            return True
        return False

    def _openai_create(self, state: ProviderState, **kwargs):
        client = self._openai_client(state.provider.id)
        for _ in range(5):
            try:
                return client.chat.completions.create(**kwargs)
            except openai.BadRequestError as exc:
                if not self._adapt(state, exc, kwargs):
                    raise
        return client.chat.completions.create(**kwargs)

    # ------------------------------------------------------------------ public API

    @staticmethod
    def _with_images(kind: str, messages: list[dict]) -> list[dict]:
        """Messages may carry {"image": {"media_type", "data"}} (base64); put it in each API's format."""
        out = []
        for message in messages:
            image = message.get("image")
            if not image:
                out.append({"role": message["role"], "content": message["content"]})
                continue
            if kind == "anthropic":
                parts = [{"type": "image", "source": {"type": "base64", "media_type": image["media_type"], "data": image["data"]}},
                         {"type": "text", "text": message["content"]}]
            else:
                parts = [{"type": "text", "text": message["content"]},
                         {"type": "image_url", "image_url": {"url": f"data:{image['media_type']};base64,{image['data']}"}}]
            out.append({"role": message["role"], "content": parts})
        return out

    def stream_reply(self, system: str, messages: list[dict], max_tokens: int = 1500) -> Iterator[tuple[str, str]]:
        """Yield ("text", chunk) events and finally ("stop", reason)."""
        state = self._check(self.active)
        has_image = any(m.get("image") for m in messages)
        messages = self._with_images(state.provider.kind, messages)
        if has_image:
            vision = state.provider.vision_model
            if vision and not _LOOKS_VISUAL.search(state.model or ""):
                # The chosen model reads text only; send the photo question to the provider's vision model.
                state = dataclasses.replace(state, model=vision, dropped=set(state.dropped))
            try:
                yield from self._stream(state, system, messages, max_tokens)
            except AIUnavailable as exc:
                # Only a rejected request means the model can't take pictures; a timeout, an
                # outage or a rate limit falls back like any other question.
                if exc.permanent or exc.status not in IMAGE_REJECTED:
                    raise
                raise ImagesUnsupported(
                    f"The current AI model ({state.model or state.provider.default_model}) can't read pictures. "
                    "Type the question instead, or ask your teacher to choose a model that understands images."
                ) from exc
            return
        yield from self._stream(state, system, messages, max_tokens)

    def _stream(self, state: ProviderState, system: str, messages: list[dict], max_tokens: int) -> Iterator[tuple[str, str]]:
        if state.provider.kind == "anthropic":
            yield from self._anthropic_stream(state, system, messages, max_tokens)
            return
        think = _ThinkFilter()
        reason = "stop"
        try:
            stream = self._openai_create(state, messages=[{"role": "system", "content": system}, *messages],
                                         stream=True, **self._openai_kwargs(state, max_tokens, 0.4))
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
            raise self._fail(state, exc) from exc
        rest = think.flush()
        if rest:
            yield "text", rest
        state.last_error = ""
        yield "stop", reason

    def complete(self, system: str, prompt: str, max_tokens: int = 2048, json_mode: bool = False,
                 pid: str | None = None) -> str:
        state = self._check(pid or self.active)
        if state.provider.kind == "anthropic":
            return self._anthropic_complete(state, system, prompt, max_tokens)
        kwargs = self._openai_kwargs(state, max_tokens, 0.3)
        if json_mode and "response_format" not in state.dropped:
            kwargs["response_format"] = {"type": "json_object"}
        try:
            response = self._openai_create(state, messages=[{"role": "system", "content": system},
                                                            {"role": "user", "content": prompt}], **kwargs)
        except openai.OpenAIError as exc:
            raise self._fail(state, exc) from exc
        state.last_error = ""
        if not response.choices:
            raise AIUnavailable(f"{state.provider.name} returned an empty reply")
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

    def test(self, pid: str | None = None) -> str:
        """A tiny request used by the teacher console's "Test connection" button."""
        pid = pid or self.active
        state = self.states[pid]
        if not state.configured:
            raise AIUnavailable(f"{state.provider.name} isn't set up yet", permanent=True)
        state.last_error = ""  # allow a retry after fixing a rejected key
        # Test the chosen provider directly; the provider students are using stays active meanwhile.
        return self.complete("You are a connection test.", "Reply with exactly: TatvaX is connected.", max_tokens=200, pid=pid)

    def list_models(self, pid: str) -> list[str]:
        """Chat models the provider offers for this key, newest names first where possible."""
        state = self.states[pid]
        if not state.configured and not (pid in ("together", "xai") and state.api_key):
            raise AIUnavailable(f"{state.provider.name} isn't set up yet", permanent=True)
        try:
            if state.provider.kind == "anthropic":
                ids = [m.id for m in self._anthropic_client().models.list()]
            else:
                ids = [m.id for m in self._openai_client(pid).models.list()]
        except Exception as exc:  # each SDK has its own error types
            raise self._fail(state, exc) from exc
        ids = [i.removeprefix("models/") for i in ids if i and not _NOT_CHAT.search(i)]
        return sorted(set(ids))

    def choose_model(self, pid: str) -> str | None:
        """When no model is chosen yet (or it no longer exists), pick one from the live list."""
        try:
            available = self.list_models(pid)
        except AIUnavailable:
            return None
        if not available:
            return None
        current = self.states[pid].model
        if current and current in available:
            return current
        preferred = [m for m, _, _ in PROVIDERS[pid].models]
        return next((m for m in preferred if m in available), available[0])

    # ------------------------------------------------------------------ Anthropic (Claude)

    def _anthropic_kwargs(self, state: ProviderState, max_tokens: int) -> dict:
        kwargs: dict = {"model": state.model or state.provider.default_model, "max_tokens": max_tokens}
        model = kwargs["model"]
        if model.startswith(("claude-opus-5", "claude-sonnet-5", "claude-fable-5", "claude-haiku-5", "claude-opus-4-7", "claude-opus-4-8")):
            kwargs["output_config"] = {"effort": "low"}  # quick, conversational replies
        if model in {"claude-opus-5-5", "claude-opus-5", "claude-fable-5-1", "claude-fable-5", "claude-sonnet-5-5"}:
            # If a safety classifier declines, the API retries on Anthropic's recommended model.
            kwargs["betas"] = ["server-side-fallback-2026-07-01"]
            kwargs["fallbacks"] = "default"
        return kwargs

    @staticmethod
    def _anthropic_text(message) -> str:
        blocks = list(message.content)
        last_switch = max((i for i, b in enumerate(blocks) if b.type == "fallback"), default=-1)
        return "".join(b.text for b in blocks[last_switch + 1:] if b.type == "text")

    def _anthropic_stream(self, state, system, messages, max_tokens):
        import anthropic

        streamed = []
        try:
            with self._anthropic_client().beta.messages.stream(
                system=system, messages=messages, **self._anthropic_kwargs(state, max_tokens)
            ) as stream:
                for text in stream.text_stream:
                    streamed.append(text)
                    yield "text", text
                final = stream.get_final_message()
        except anthropic.APIError as exc:
            raise self._fail(state, exc) from exc
        if final.stop_reason == "refusal":
            raise AIUnavailable("Claude declined this request")
        state.last_error = ""
        yield "stop", final.stop_reason or "end_turn"

    def _anthropic_complete(self, state, system, prompt, max_tokens):
        import anthropic

        try:
            response = self._anthropic_client().beta.messages.create(
                system=system, messages=[{"role": "user", "content": prompt}], **self._anthropic_kwargs(state, max_tokens)
            )
        except anthropic.APIError as exc:
            raise self._fail(state, exc) from exc
        if response.stop_reason == "refusal":
            raise AIUnavailable("Claude declined this request")
        state.last_error = ""
        return self._anthropic_text(response).strip()
