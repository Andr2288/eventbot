"""Шифрування чутливих полів (title, description) у БД."""

import os

from cryptography.fernet import Fernet, InvalidToken

_fernet: Fernet | None = None
_loaded = False


def _get_fernet() -> Fernet | None:
    global _fernet, _loaded
    if _loaded:
        return _fernet
    _loaded = True
    key = os.environ.get("ENCRYPTION_KEY", "").strip()
    if key:
        _fernet = Fernet(key.encode())
    return _fernet


def encrypt_field(value: str | None) -> str | None:
    if not value:
        return value
    f = _get_fernet()
    if not f:
        return value
    return f.encrypt(value.encode()).decode()


def decrypt_field(value: str | None) -> str | None:
    if not value:
        return value
    f = _get_fernet()
    if not f:
        return value
    try:
        return f.decrypt(value.encode()).decode()
    except InvalidToken:
        return value


def decrypt_event(event: dict) -> dict:
    event["title"] = decrypt_field(event.get("title"))
    event["description"] = decrypt_field(event.get("description"))
    return event


def reset_encryption_cache() -> None:
    """Скидання кешу (для тестів)."""
    global _fernet, _loaded
    _fernet = None
    _loaded = False
