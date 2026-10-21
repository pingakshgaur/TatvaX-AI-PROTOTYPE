"""Runtime configuration, read from environment variables (and an optional .env file)."""

import os
import secrets
from datetime import timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _env_bool(name: str, default: bool | None = None) -> bool | None:
    value = os.environ.get(name)
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _load_secret_key(instance_dir: Path) -> str:
    """Use TATVAX_SECRET_KEY if set, otherwise a random key persisted in the instance folder."""
    configured = os.environ.get("TATVAX_SECRET_KEY")
    if configured:
        return configured
    key_file = instance_dir / "secret_key"
    if not key_file.exists():
        # Several worker processes may start at once. Write the key to a private temporary file and
        # link it into place, which only one of them can do; the others then read the winner's key.
        tmp = instance_dir / f".secret_key.{os.getpid()}.{secrets.token_hex(4)}"
        tmp.write_text(secrets.token_hex(32), encoding="utf-8")
        try:
            os.chmod(tmp, 0o600)
            os.link(tmp, key_file)
        except FileExistsError:
            pass
        except OSError:  # file systems without hard links
            try:
                with open(key_file, "x", encoding="utf-8") as handle:
                    handle.write(tmp.read_text(encoding="utf-8"))
            except FileExistsError:
                pass
        finally:
            tmp.unlink(missing_ok=True)
    return key_file.read_text(encoding="utf-8").strip()


def build_config(overrides: dict | None = None) -> dict:
    overrides = overrides or {}
    instance_dir = Path(overrides.get("INSTANCE_DIR") or os.environ.get("TATVAX_INSTANCE_DIR") or PROJECT_ROOT / "instance")
    instance_dir.mkdir(parents=True, exist_ok=True)


    config = {
        "INSTANCE_DIR": instance_dir,
        "SECRET_KEY": _load_secret_key(instance_dir),
        "DATABASE": os.environ.get("TATVAX_DATABASE") or str(instance_dir / "tatvax.db"),
        "CONTENT_DIR": Path(os.environ.get("TATVAX_CONTENT_DIR") or PROJECT_ROOT / "content"),
        "FRONTEND_DIST": Path(os.environ.get("TATVAX_FRONTEND_DIST") or PROJECT_ROOT / "frontend" / "dist"),
        # The AI tutor uses a free NVIDIA API key, entered in the teacher console or set here.
        # TATVAX_AI=off disables it entirely (study-notes answers only).
        "AI_ALLOWED": _env_bool("TATVAX_AI", True),
        "SHARED_RATE_LIMIT": bool(_env_bool("TATVAX_SHARED_RATE_LIMIT", False)),
        "NVIDIA_API_KEY": os.environ.get("NVIDIA_API_KEY", ""),
        "AI_MODEL": os.environ.get("TATVAX_MODEL", ""),
        "TEACHER_CODE": os.environ.get("TATVAX_TEACHER_CODE", ""),
        # Without an AI provider, translation falls back to free public web services (Google's
        # translate endpoint, then MyMemory), which receive the text. TATVAX_WEB_TRANSLATION=off stops that.
        "WEB_TRANSLATION": bool(_env_bool("TATVAX_WEB_TRANSLATION", True)),
        "CHAT_RATE_LIMIT": int(os.environ.get("TATVAX_CHAT_RATE_LIMIT", "20")),  # messages per minute per user
        "MAX_MESSAGE_CHARS": 2000,
        "MAX_CONTENT_LENGTH": 2 * 1024 * 1024,
        "SESSION_COOKIE_HTTPONLY": True,
        "SESSION_COOKIE_SAMESITE": "Lax",
        "SESSION_COOKIE_SECURE": bool(_env_bool("TATVAX_SECURE_COOKIES", False)),
        "PERMANENT_SESSION_LIFETIME": timedelta(days=30),
        "JSON_SORT_KEYS": False,
        "TESTING": False,
    }
    config.update(overrides)
    return config
