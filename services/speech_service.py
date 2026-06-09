"""Розпізнавання голосу через OpenAI Whisper API."""

import os
from pathlib import Path

from aiogram import Bot
from openai import AsyncOpenAI

from utils.env import require

TMP_DIR = Path(__file__).resolve().parent.parent / "tmp"


def _client() -> AsyncOpenAI:
    return AsyncOpenAI(api_key=require("OPENAI_API_KEY"))


async def transcribe_telegram_voice(bot: Bot, file_id: str) -> str:
    """Завантажити голосове з Telegram і повернути текст."""
    TMP_DIR.mkdir(exist_ok=True)
    tg_file = await bot.get_file(file_id)
    suffix = Path(tg_file.file_path or "voice.ogg").suffix or ".ogg"
    safe_id = file_id.replace("/", "_")
    tmp_path = TMP_DIR / f"voice_{safe_id}{suffix}"

    try:
        await bot.download_file(tg_file.file_path, tmp_path)
        with open(tmp_path, "rb") as audio:
            result = await _client().audio.transcriptions.create(
                model="whisper-1",
                file=audio,
                language="uk",
            )
        return result.text.strip()
    finally:
        if tmp_path.exists():
            tmp_path.unlink()
