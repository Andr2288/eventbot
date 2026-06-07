"""Текстові команди бота."""

from datetime import date

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

import db.user_repo as user_repo
from handlers.keyboards import main_menu, admin_menu
from services.event_service import (
    get_events_today, get_events_week, get_all_events, format_event
)
from utils.env import get_admin_ids
from utils.logger import log_action

router = Router()


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    log_action(message.from_user.id, "help")
    await message.answer(
        "📖 <b>Довідка EventBot</b>\n\n"
        "<b>Команди:</b>\n"
        "/start — головне меню\n"
        "/help — ця довідка\n"
        "/today — події на сьогодні\n"
        "/week — події на тиждень\n"
        "/all — всі майбутні події\n"
        "/admin — панель адміністратора\n\n"
        "<b>Можливості через меню:</b>\n"
        "• Створити подію (назва, дата, час, опис)\n"
        "• Нагадування: за 10хв / 1год / 1день / власний час\n"
        "• Перегляд: сьогодні / тиждень / всі\n"
        "• Редагування дати та часу події\n"
        "• Видалення події",
        reply_markup=main_menu(),
    )


@router.message(Command("today"))
async def cmd_today(message: Message) -> None:
    uid = message.from_user.id
    log_action(uid, "view_today")
    events = await get_events_today(uid)
    if not events:
        await message.answer("📭 Сьогодні подій немає.", reply_markup=main_menu())
        return
    lines = [f"📅 <b>Сьогодні, {date.today().strftime('%d.%m.%Y')}</b>\n"]
    lines += [format_event(e, i + 1) for i, e in enumerate(events)]
    await message.answer("\n\n".join(lines), reply_markup=main_menu())


@router.message(Command("week"))
async def cmd_week(message: Message) -> None:
    uid = message.from_user.id
    log_action(uid, "view_week")
    events = await get_events_week(uid)
    if not events:
        await message.answer("📭 На цьому тижні подій немає.", reply_markup=main_menu())
        return
    lines = ["📆 <b>Події на тиждень:</b>\n"]
    lines += [format_event(e, i + 1) for i, e in enumerate(events)]
    await message.answer("\n\n".join(lines), reply_markup=main_menu())


@router.message(Command("all"))
async def cmd_all(message: Message) -> None:
    uid = message.from_user.id
    log_action(uid, "view_all")
    events = await get_all_events(uid)
    if not events:
        await message.answer("📭 Майбутніх подій немає.", reply_markup=main_menu())
        return
    lines = ["📋 <b>Всі майбутні події:</b>\n"]
    lines += [format_event(e, i + 1) for i, e in enumerate(events)]
    await message.answer("\n\n".join(lines), reply_markup=main_menu())


@router.message(Command("admin"))
async def cmd_admin(message: Message) -> None:
    uid = message.from_user.id
    if uid not in get_admin_ids():
        await message.answer("⛔ Доступ заборонено.")
        return
    log_action(uid, "admin_panel")
    count = await user_repo.get_users_count()
    await message.answer(
        f"🔧 <b>Панель адміністратора</b>\n\nКористувачів: <b>{count}</b>",
        reply_markup=admin_menu(),
    )
