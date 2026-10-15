"""Server-side text-to-speech with gTTS, used when the browser has no voice for a language.

Audio is generated in memory and streamed back, so nothing is written to disk."""

import io
import logging
import re
import unicodedata
from functools import lru_cache

log = logging.getLogger(__name__)

MAX_SPEECH_CHARS = 2500

_LATEX_REPLACEMENTS = [
    (re.compile(r"\\frac\{([^{}]*)\}\{([^{}]*)\}"), r"\1 / \2"),
    (re.compile(r"\\sqrt\{([^{}]*)\}"), r"√\1"),
    (re.compile(r"\\(times|cdot)"), " × "),
    (re.compile(r"\\div"), " ÷ "),
    (re.compile(r"\\(leq|le)\b"), " ≤ "),
    (re.compile(r"\\(geq|ge)\b"), " ≥ "),
    (re.compile(r"\\pi\b"), "π"),
    (re.compile(r"\^\{?2\}?"), "²"),
    (re.compile(r"\^\{?3\}?"), "³"),
    (re.compile(r"\\[a-zA-Z]+"), " "),
]


@lru_cache(maxsize=1)
def supported_languages() -> frozenset:
    try:
        from gtts.lang import tts_langs

        return frozenset(tts_langs())
    except Exception:  # gTTS missing or its language list failed to load
        log.warning("gTTS is unavailable; server-side speech is disabled")
        return frozenset()


def clean_for_speech(text: str) -> str:
    """Strip Markdown, LaTeX syntax and emoji while keeping every letter, including the
    vowel signs (matras) of Indic scripts."""
    text = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)          # links -> link text
    for pattern, replacement in _LATEX_REPLACEMENTS:
        text = pattern.sub(replacement, text)
    text = re.sub(r"[$`*_#>{}|~]", " ", text)
    text = re.sub(r"^\s*[-+]\s+", "", text, flags=re.MULTILINE)      # bullet markers
    text = "".join(ch for ch in text if unicodedata.category(ch) not in {"So", "Cs", "Co"})
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > MAX_SPEECH_CHARS:
        cut = text.rfind(".", 0, MAX_SPEECH_CHARS)
        text = text[: cut + 1 if cut > MAX_SPEECH_CHARS // 2 else MAX_SPEECH_CHARS]
    return text


@lru_cache(maxsize=64)
def synthesize(text: str, language: str) -> bytes:
    from gtts import gTTS

    buffer = io.BytesIO()
    gTTS(text=text, lang=language, slow=False).write_to_fp(buffer)
    return buffer.getvalue()
