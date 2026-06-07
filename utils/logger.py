"""Утиліта логування дій користувачів."""

import logging
import os
from datetime import datetime

logger = logging.getLogger("actions")

LOG_FILE = os.path.join(os.path.dirname(__file__), "..", "logs", "actions.log")


def log_action(user_id: int, action: str, detail: str = "") -> None:
    """Логувати дію користувача у файл та консоль."""
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{timestamp}] user={user_id} action={action}"
    if detail:
        entry += f" | {detail}"
    logger.info(entry)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(entry + "\n")
