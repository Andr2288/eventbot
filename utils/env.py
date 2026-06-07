"""Завантаження .env файлу."""

import os
from pathlib import Path


def load_env() -> None:
    env_path = Path(__file__).parent.parent / ".env"
    if not env_path.exists():
        return
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())


def require(key: str) -> str:
    value = os.environ.get(key)
    if not value:
        raise RuntimeError(f"Змінна '{key}' не знайдена у .env")
    return value


def get_admin_ids() -> set[int]:
    """Повертає Telegram ID адмінів з ADMIN_IDS (через кому)."""
    raw = os.environ.get("ADMIN_IDS", "")
    return {int(x) for x in raw.split(",") if x.strip().isdigit()}
