"""Supported languages and script-based language detection."""

import unicodedata

# code: (English name, native name, BCP-47 speech locale, text direction)
LANGUAGES = {
    "en": ("English", "English", "en-IN", "ltr"),
    "hi": ("Hindi", "हिन्दी", "hi-IN", "ltr"),
    "bn": ("Bengali", "বাংলা", "bn-IN", "ltr"),
    "mr": ("Marathi", "मराठी", "mr-IN", "ltr"),
    "te": ("Telugu", "తెలుగు", "te-IN", "ltr"),
    "ta": ("Tamil", "தமிழ்", "ta-IN", "ltr"),
    "gu": ("Gujarati", "ગુજરાતી", "gu-IN", "ltr"),
    "kn": ("Kannada", "ಕನ್ನಡ", "kn-IN", "ltr"),
    "ml": ("Malayalam", "മലയാളം", "ml-IN", "ltr"),
    "pa": ("Punjabi", "ਪੰਜਾਬੀ", "pa-IN", "ltr"),
    "or": ("Odia", "ଓଡ଼ିଆ", "or-IN", "ltr"),
    "as": ("Assamese", "অসমীয়া", "as-IN", "ltr"),
    "ur": ("Urdu", "اردو", "ur-IN", "rtl"),
    "ne": ("Nepali", "नेपाली", "ne-NP", "ltr"),
    "sa": ("Sanskrit", "संस्कृतम्", "sa-IN", "ltr"),
    "gom": ("Konkani", "कोंकणी", "kok-IN", "ltr"),
}

DEFAULT_LANGUAGE = "en"

# Unicode block for each script, and the language it maps to by default.
_SCRIPTS = [
    ("ऀ", "ॿ", "hi"),  # Devanagari (Hindi, Marathi)
    ("ঀ", "৿", "bn"),  # Bengali-Assamese
    ("਀", "੿", "pa"),  # Gurmukhi
    ("઀", "૿", "gu"),  # Gujarati
    ("଀", "୿", "or"),  # Odia
    ("஀", "௿", "ta"),  # Tamil
    ("ఀ", "౿", "te"),  # Telugu
    ("ಀ", "೿", "kn"),  # Kannada
    ("ഀ", "ൿ", "ml"),  # Malayalam
    ("؀", "ۿ", "ur"),  # Arabic script (Urdu)
]

_MARATHI_WORDS = ("आहे", "आहेत", "नाही", "काय", "कसे", "मला", "तुम्ही", "आणि", "मध्ये")
_NEPALI_WORDS = ("छ", "हुन्छ", "गर्नु", "तपाईं", "हुँदै", "भएको", "गर्छ")
_ASSAMESE_LETTERS = ("ৰ", "ৱ")  # ৰ ৱ only occur in Assamese


def _words(text: str) -> list[str]:
    """Words in any script (letters, combining vowel signs and digits), split at spaces and punctuation."""
    out, current = [], []
    for ch in text:
        if unicodedata.category(ch)[0] in "LMN":
            current.append(ch)
        elif current:
            out.append("".join(current))
            current = []
    if current:
        out.append("".join(current))
    return out


def is_supported(code: str | None) -> bool:
    return code in LANGUAGES


def normalize(code: str | None) -> str:
    return code if code in LANGUAGES else DEFAULT_LANGUAGE


def english_name(code: str) -> str:
    return LANGUAGES.get(code, LANGUAGES[DEFAULT_LANGUAGE])[0]


def as_list() -> list[dict]:
    return [
        {"code": code, "name": name, "native": native, "speech": speech, "dir": direction}
        for code, (name, native, speech, direction) in LANGUAGES.items()
    ]


def detect_language(text: str) -> str:
    """Guess the language from the script used. Latin text is treated as English."""
    letters = [ch for ch in text if not ch.isspace() and not ch.isdigit()]
    if not letters:
        return DEFAULT_LANGUAGE

    counts: dict[str, int] = {}
    for ch in letters:
        for start, end, lang in _SCRIPTS:
            if start <= ch <= end:
                counts[lang] = counts.get(lang, 0) + 1
                break
    if not counts:
        return DEFAULT_LANGUAGE

    lang, count = max(counts.items(), key=lambda item: item[1])
    if count / len(letters) < 0.2:
        return DEFAULT_LANGUAGE
    # Whole words only: "मला" is Marathi, but it is also the end of the Hindi "हमला" and "कमला".
    tokens = set(_words(text))
    if lang == "hi" and ("ळ" in text or tokens & set(_MARATHI_WORDS)):
        return "mr"
    if lang == "hi" and tokens & set(_NEPALI_WORDS):
        return "ne"
    if lang == "bn" and any(letter in text for letter in _ASSAMESE_LETTERS):
        return "as"
    return lang
