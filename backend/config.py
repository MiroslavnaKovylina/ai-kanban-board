import os
from pathlib import Path

SESSION_COOKIE_NAME = "kanban_session"


def _get_int_env(name: str, default: int, minimum: int = 0) -> int:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        value = int(raw_value)
    except ValueError:
        return default
    return max(value, minimum)


def _get_bool_env(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def _session_ttl_days() -> int:
    return _get_int_env("SESSION_TTL_DAYS", 7, minimum=1)


def _is_local_development() -> bool:
    environment = os.getenv("ENVIRONMENT", os.getenv("APP_ENV", "local")).strip().lower()
    return environment in {"local", "dev", "development", "test"}


def _session_cookie_secure() -> bool:
    raw_value = os.getenv("SESSION_COOKIE_SECURE")
    if raw_value is not None:
        return _get_bool_env("SESSION_COOKIE_SECURE", False)
    # Local Docker runs on HTTP. Production must set SESSION_COOKIE_SECURE=true.
    return not _is_local_development()


def _allowed_ai_origins() -> set[str]:
    configured = os.getenv(
        "AI_ALLOWED_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000,http://localhost:8000,http://127.0.0.1:8000",
    )
    return {item.strip().rstrip("/") for item in configured.split(",") if item.strip()}


def _load_project_env() -> None:
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value
