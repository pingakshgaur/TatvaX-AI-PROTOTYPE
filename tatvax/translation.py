"""Translation: the AI model when configured, otherwise free public endpoints (Google gtx, then MyMemory)."""

import logging
from functools import lru_cache

import requests

from . import languages
from .ai import AIService, AIUnavailable

log = logging.getLogger(__name__)

_TIMEOUT = 8


class TranslationError(Exception):
    pass


class Translator:
    def __init__(self, ai: AIService):
        self.ai = ai

    def translate(self, text: str, target: str, source: str = "auto") -> tuple[str, str]:
        """Return (translated_text, engine). Raises TranslationError if every engine fails."""
        text = text.strip()
        if not text:
            return text, "none"
        target = languages.normalize(target)
        if source == "auto":
            source = languages.detect_language(text)
        if source == target:
            return text, "none"

        if self.ai.available:
            try:
                return self._translate_ai(text, source, target), "ai"
            except AIUnavailable as exc:
                log.info("AI translation unavailable (%s); trying web endpoints", exc)

        for engine, func in (("google", _google), ("mymemory", _mymemory)):
            try:
                result = func(text, source, target)
                if result and result.strip():
                    return result, engine
            except Exception as exc:  # network errors, bad JSON, rate limits
                log.info("%s translation failed: %s", engine, exc)
        raise TranslationError("All translation services are unavailable")

    def _translate_ai(self, text: str, source: str, target: str) -> str:
        system = (
            "You are a translator for an Indian school learning app. Translate the user's text from "
            f"{languages.english_name(source)} into {languages.english_name(target)}. Keep Markdown formatting, "
            "numbers, formulas and LaTeX unchanged. Use simple words a school student understands. "
            "Reply with the translation only."
        )
        return self.ai.complete(system, text, max_tokens=4096)


_GOOGLE_CHUNK = 3500  # characters per request; the endpoint keeps line breaks within a request


@lru_cache(maxsize=512)
def _google(text: str, source: str, target: str) -> str:
    chunks, current = [], ""
    for line in text.split("\n"):
        if current and len(current) + len(line) + 1 > _GOOGLE_CHUNK:
            chunks.append(current)
            current = line
        else:
            current = f"{current}\n{line}" if current else line
    chunks.append(current)

    out = []
    for chunk in chunks:
        if not chunk.strip():
            out.append(chunk)
            continue
        response = requests.post(
            "https://translate.googleapis.com/translate_a/single",
            params={"client": "gtx", "sl": source, "tl": target, "dt": "t"},
            data={"q": chunk},
            timeout=_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
        out.append("".join(part[0] for part in data[0] if part and part[0]))
    return "\n".join(out)


@lru_cache(maxsize=512)
def _mymemory(text: str, source: str, target: str) -> str:
    if len(text) > 480:  # MyMemory's free tier rejects long queries
        raise TranslationError("Text too long for MyMemory")
    response = requests.get(
        "https://api.mymemory.translated.net/get",
        params={"q": text, "langpair": f"{source}|{target}"},
        timeout=_TIMEOUT,
    )
    response.raise_for_status()
    data = response.json()
    if int(data.get("responseStatus", 200)) != 200:
        raise TranslationError(data.get("responseDetails", "MyMemory error"))
    return data["responseData"]["translatedText"]
