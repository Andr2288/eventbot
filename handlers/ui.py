"""Допоміжні функції для оновлення повідомлень у callback."""

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery


async def edit_or_answer(cb: CallbackQuery, text: str, reply_markup=None) -> None:
    """edit_text для тексту; для фото/без тексту — нове повідомлення."""
    msg = cb.message
    if msg.text is not None:
        try:
            await msg.edit_text(text, reply_markup=reply_markup)
            return
        except TelegramBadRequest as e:
            if "message is not modified" in str(e).lower():
                return
            if "there is no text" not in str(e).lower():
                raise

    if msg.photo or msg.document:
        try:
            await msg.delete()
        except TelegramBadRequest:
            pass

    await msg.answer(text, reply_markup=reply_markup)
