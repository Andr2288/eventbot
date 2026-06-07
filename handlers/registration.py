"""Авторизація / перший запуск."""

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

import db.user_repo as user_repo
from handlers.keyboards import main_menu
from utils.logger import log_action

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    user_id = message.from_user.id
    username = message.from_user.username or ""
    full_name = message.from_user.full_name or "Користувач"

    await user_repo.get_or_create_user(user_id, username, full_name)
    log_action(user_id, "start")

    name = full_name.split()[0]
    await message.answer(
        f"Привіт, <b>{name}</b>! 👋\n\n"
        "Я — EventBot. Допоможу тобі:\n"
        "• 📅 Планувати події\n"
        "• 🔔 Надсилати нагадування\n"
        "• 📋 Переглядати розклад\n\n"
        "Що хочеш зробити?",
        reply_markup=main_menu(),
    )
