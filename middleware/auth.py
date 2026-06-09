"""Доступ лише для зареєстрованих користувачів (після /start)."""

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

import db.user_repo as user_repo


async def registration_block_reason(user_id: int, text: str | None = None) -> str | None:
    """Повертає текст відмови або None, якщо доступ дозволено."""
    if await user_repo.user_exists(user_id):
        return None
    if text and text.startswith("/start"):
        return None
    return "Спочатку натисни /start для реєстрації."


class RegisteredUserMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = None
        if isinstance(event, Message) and event.from_user:
            user = event.from_user
        elif isinstance(event, CallbackQuery) and event.from_user:
            user = event.from_user

        if not user:
            return await handler(event, data)

        text = event.text if isinstance(event, Message) else None
        reason = await registration_block_reason(user.id, text)
        if reason is None:
            return await handler(event, data)

        if isinstance(event, Message):
            await event.answer(reason)
            return None

        if isinstance(event, CallbackQuery):
            await event.answer("Спочатку натисни /start.", show_alert=True)
            return None

        return await handler(event, data)
