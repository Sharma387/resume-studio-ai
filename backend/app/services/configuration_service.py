"""Configuration abstraction for runtime settings management.

Reads from and writes to the application's configuration source.
Currently backed by .env file via python-dotenv.
Future: can be backed by PostgreSQL without changing callers.
"""

from pathlib import Path
from typing import Any

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

ENV_FILE = Path(__file__).resolve().parent.parent.parent / ".env"


def _read_env() -> dict[str, str]:
    """Read current .env file into a dict."""
    if not ENV_FILE.exists():
        return {}
    result: dict[str, str] = {}
    with open(ENV_FILE) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            result[key.strip()] = value.strip()
    return result


def _write_env(updates: dict[str, str]) -> None:
    """Update specific keys in .env while preserving other content."""
    if not ENV_FILE.exists():
        ENV_FILE.write_text("")
    lines = ENV_FILE.read_text().splitlines(keepends=True)
    updated_keys = set(updates.keys())
    new_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            new_lines.append(line)
            continue
        key = stripped.split("=", 1)[0].strip()
        if key in updated_keys:
            new_lines.append(f"{key}={updates[key]}\n")
            updated_keys.discard(key)
        else:
            new_lines.append(line)
    for key in updated_keys:
        new_lines.append(f"{key}={updates[key]}\n")
    ENV_FILE.write_text("".join(new_lines))
    logger.info("Configuration persisted", file=str(ENV_FILE), keys=list(updates.keys()))


def get(key: str) -> Any:
    return getattr(settings, key, None)


def get_all() -> dict[str, Any]:
    return {k: getattr(settings, k) for k in dir(settings) if not k.startswith("_") and k != "model_config"}


def set_storage_backend(backend: str) -> dict[str, Any]:
    """Switch the active storage backend at runtime and persist the change.

    Returns the updated configuration dict.
    """
    if backend not in ("json", "postgres"):
        raise ValueError(f"Invalid backend '{backend}'. Must be 'json' or 'postgres'.")

    old_backend = settings.storage_backend
    settings.storage_backend = backend
    _write_env({"STORAGE_BACKEND": backend})

    logger.info(
        "Storage backend switched",
        previous=old_backend,
        current=backend,
    )

    return {
        "previous": old_backend,
        "current": backend,
        "restart_required": True,
    }


def set_database_url(url: str) -> None:
    settings.database_url = url
    _write_env({"DATABASE_URL": url})
    logger.info("Database URL updated")


def set_ai_config(updates: dict) -> dict:
    """Update AI configuration settings at runtime and persist.

    Accepted keys: model, endpoint, timeout, max_retries.
    """
    env_updates: dict[str, str] = {}
    if "model" in updates:
        settings.omniroute_model = updates["model"]
        env_updates["OMNIROUTE_MODEL"] = str(updates["model"])
    if "endpoint" in updates:
        settings.omniroute_api_url = updates["endpoint"]
        env_updates["OMNIROUTE_API_URL"] = str(updates["endpoint"])
    if "timeout" in updates:
        settings.omniroute_timeout = int(updates["timeout"])
        env_updates["OMNIROUTE_TIMEOUT"] = str(int(updates["timeout"]))
    if "max_retries" in updates:
        settings.omniroute_max_retries = int(updates["max_retries"])
        env_updates["OMNIROUTE_MAX_RETRIES"] = str(int(updates["max_retries"]))

    if env_updates:
        _write_env(env_updates)
        logger.info("AI configuration updated", keys=list(env_updates.keys()))

    return {
        "endpoint": settings.omniroute_api_url,
        "model": settings.omniroute_model,
        "timeout": settings.omniroute_timeout,
        "max_retries": settings.omniroute_max_retries,
        "restart_required": bool(env_updates),
    }
