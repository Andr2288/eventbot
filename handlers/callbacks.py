"""Обробники inline-кнопок та FSM діалогів."""

import os
import shutil
from datetime import date, datetime, timedelta

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, FSInputFile, Message

import db.event_repo as event_repo
import db.user_repo as user_repo
from db.database import DB_PATH
from handlers.keyboards import (
    admin_menu, back_to_main, calendar_keyboard, confirm_keyboard,
    events_list_keyboard, events_view_menu, main_menu,
    reminder_type_keyboard, skip_or_back, time_keyboard,
)
from services.event_service import (
    add_reminder_for_event, create_event, delete_event,
    format_event, get_all_events, get_events_today, get_events_week,
    parse_date, parse_time, update_event_datetime,
)
from utils.env import get_admin_ids
from utils.logger import log_action

router = Router()


async def safe_edit_text(message, text: str, reply_markup=None) -> bool:
    """Редагує повідомлення; повертає False, якщо текст не змінився."""
    try:
        await message.edit_text(text, reply_markup=reply_markup)
        return True
    except TelegramBadRequest as e:
        if "message is not modified" in str(e).lower():
            return False
        raise


# ── FSM States ──────────────────────────────────────────────
class CreateEvent(StatesGroup):
    title       = State()
    date_pick   = State()
    time_pick   = State()
    description = State()
    reminder    = State()
    reminder_custom = State()


class EditEvent(StatesGroup):
    pick_event  = State()
    date_pick   = State()
    time_pick   = State()


class DeleteEvent(StatesGroup):
    confirm     = State()


class AddReminder(StatesGroup):
    pick_event  = State()
    pick_type   = State()
    custom_min  = State()


# ── Головне меню ────────────────────────────────────────────
@router.callback_query(F.data == "menu_main")
async def cb_main_menu(cb: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await cb.message.edit_text("📋 Головне меню. Що хочеш зробити?", reply_markup=main_menu())


# ── Перегляд подій ──────────────────────────────────────────
@router.callback_query(F.data == "events_view")
async def cb_events_view(cb: CallbackQuery) -> None:
    await cb.message.edit_text("🔍 Перегляд подій. Обери варіант:", reply_markup=events_view_menu())


@router.callback_query(F.data == "view_today")
async def cb_view_today(cb: CallbackQuery) -> None:
    uid = cb.from_user.id
    log_action(uid, "view_today")
    events = await get_events_today(uid)
    if not events:
        await cb.message.edit_text("📭 Сьогодні подій немає.", reply_markup=events_view_menu())
        return
    lines = [f"📅 <b>Сьогодні, {date.today().strftime('%d.%m.%Y')}</b>\n"]
    lines += [format_event(e, i + 1) for i, e in enumerate(events)]
    await cb.message.edit_text("\n\n".join(lines), reply_markup=events_view_menu())


@router.callback_query(F.data == "view_week")
async def cb_view_week(cb: CallbackQuery) -> None:
    uid = cb.from_user.id
    log_action(uid, "view_week")
    events = await get_events_week(uid)
    if not events:
        await cb.message.edit_text("📭 На цьому тижні подій немає.", reply_markup=events_view_menu())
        return
    lines = ["📆 <b>Події на тиждень:</b>\n"]
    lines += [format_event(e, i + 1) for i, e in enumerate(events)]
    await cb.message.edit_text("\n\n".join(lines), reply_markup=events_view_menu())


@router.callback_query(F.data == "view_all")
async def cb_view_all(cb: CallbackQuery) -> None:
    uid = cb.from_user.id
    log_action(uid, "view_all")
    events = await get_all_events(uid)
    if not events:
        await cb.message.edit_text("📭 Майбутніх подій немає.", reply_markup=events_view_menu())
        return
    lines = ["📋 <b>Всі майбутні події:</b>\n"]
    lines += [format_event(e, i + 1) for i, e in enumerate(events)]
    await cb.message.edit_text("\n\n".join(lines), reply_markup=events_view_menu())


# ── Створення події ─────────────────────────────────────────
@router.callback_query(F.data == "event_create")
async def cb_event_create(cb: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(CreateEvent.title)
    await cb.message.edit_text(
        "📅 <b>Створення нової події</b>\n\nВведи назву події:",
        reply_markup=back_to_main(),
    )


@router.message(CreateEvent.title)
async def fsm_event_title(message: Message, state: FSMContext) -> None:
    title = message.text.strip()
    if not title:
        await message.answer("Назва не може бути порожньою. Спробуй ще раз:")
        return
    await state.update_data(title=title)
    await state.set_state(CreateEvent.date_pick)
    today = date.today()
    await message.answer(
        f"✅ Назва: <b>{title}</b>\n\n📆 Тепер обери дату події:",
        reply_markup=calendar_keyboard(today.year, today.month),
    )


# ── Календар ────────────────────────────────────────────────
@router.callback_query(F.data == "cal_ignore")
async def cb_cal_ignore(cb: CallbackQuery) -> None:
    await cb.answer()


@router.callback_query(F.data.startswith("cal_prev_"))
async def cb_cal_prev(cb: CallbackQuery) -> None:
    _, _, y, m = cb.data.split("_")
    y, m = int(y), int(m) - 1
    if m == 0:
        m, y = 12, y - 1
    await cb.message.edit_reply_markup(reply_markup=calendar_keyboard(y, m))


@router.callback_query(F.data.startswith("cal_next_"))
async def cb_cal_next(cb: CallbackQuery) -> None:
    _, _, y, m = cb.data.split("_")
    y, m = int(y), int(m) + 1
    if m == 13:
        m, y = 1, y + 1
    await cb.message.edit_reply_markup(reply_markup=calendar_keyboard(y, m))


@router.callback_query(F.data.startswith("cal_pick_"))
async def cb_cal_pick(cb: CallbackQuery, state: FSMContext) -> None:
    parts = cb.data.split("_")
    y, m, d = int(parts[2]), int(parts[3]), int(parts[4])
    picked = date(y, m, d)
    date_str = picked.strftime("%d.%m.%Y")
    await state.update_data(date_str=date_str, db_date=picked.isoformat())

    current = await state.get_state()
    if current == CreateEvent.date_pick:
        await state.set_state(CreateEvent.time_pick)
    elif current == EditEvent.date_pick:
        await state.set_state(EditEvent.time_pick)

    await cb.message.edit_text(
        f"✅ Дата: <b>{date_str}</b>\n\n⏰ Обери час події (або пропусти):",
        reply_markup=time_keyboard("event"),
    )


# ── Time picker ─────────────────────────────────────────────
@router.callback_query(F.data.startswith("time_h_"))
async def cb_time_h(cb: CallbackQuery) -> None:
    _, _, step, h, m = cb.data.split("_")
    await cb.message.edit_reply_markup(reply_markup=time_keyboard(step, int(h), int(m)))


@router.callback_query(F.data.startswith("time_m_"))
async def cb_time_m(cb: CallbackQuery) -> None:
    _, _, step, h, m = cb.data.split("_")
    await cb.message.edit_reply_markup(reply_markup=time_keyboard(step, int(h), int(m)))


@router.callback_query(F.data.startswith("time_confirm_"))
async def cb_time_confirm(cb: CallbackQuery, state: FSMContext) -> None:
    parts = cb.data.split("_")
    step, h, m = parts[2], int(parts[3]), int(parts[4])
    time_str = f"{h:02d}:{m:02d}"
    await state.update_data(time_str=time_str)

    current = await state.get_state()
    if current == CreateEvent.time_pick:
        await state.set_state(CreateEvent.description)
        await cb.message.edit_text(
            f"✅ Час: <b>{time_str}</b>\n\n📝 Введи опис події (або натисни «Пропустити»):",
            reply_markup=skip_or_back(),
        )
    elif current == EditEvent.time_pick:
        await _finish_edit(cb, state, time_str)


@router.callback_query(F.data.startswith("time_skip_"))
async def cb_time_skip(cb: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(time_str=None)

    current = await state.get_state()
    if current == CreateEvent.time_pick:
        await state.set_state(CreateEvent.description)
        await cb.message.edit_text(
            "⏭ Час не вказано.\n\n📝 Введи опис події (або натисни «Пропустити»):",
            reply_markup=skip_or_back(),
        )
    elif current == EditEvent.time_pick:
        await _finish_edit(cb, state, None)


# ── Опис події ──────────────────────────────────────────────
@router.callback_query(F.data == "skip_input")
async def cb_skip_input(cb: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(description=None)
    await _finish_create(cb, state)


@router.message(CreateEvent.description)
async def fsm_event_description(message: Message, state: FSMContext) -> None:
    await state.update_data(description=message.text.strip())
    await _finish_create_msg(message, state)


async def _finish_create(cb: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    uid = cb.from_user.id
    ok, err, event_id = await create_event(
        uid, data["title"], data["date_str"],
        data.get("time_str"), data.get("description"),
    )
    if not ok:
        await cb.message.edit_text(f"❌ {err}", reply_markup=main_menu())
        await state.clear()
        return
    log_action(uid, "create_event", data["title"])
    time_part = f" о {data['time_str']}" if data.get("time_str") else ""
    await state.update_data(last_event_id=event_id)
    await state.set_state(CreateEvent.reminder)
    await cb.message.edit_text(
        f"✅ Подію створено!\n\n"
        f"📅 <b>{data['title']}</b>\n"
        f"🗓 {data['date_str']}{time_part}\n\n"
        "🔔 Додати нагадування?",
        reply_markup=reminder_type_keyboard(event_id),
    )


async def _finish_create_msg(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    uid = message.from_user.id
    ok, err, event_id = await create_event(
        uid, data["title"], data["date_str"],
        data.get("time_str"), data.get("description"),
    )
    if not ok:
        await message.answer(f"❌ {err}", reply_markup=main_menu())
        await state.clear()
        return
    log_action(uid, "create_event", data["title"])
    time_part = f" о {data['time_str']}" if data.get("time_str") else ""
    await state.update_data(last_event_id=event_id)
    await state.set_state(CreateEvent.reminder)
    await message.answer(
        f"✅ Подію створено!\n\n"
        f"📅 <b>{data['title']}</b>\n"
        f"🗓 {data['date_str']}{time_part}\n\n"
        "🔔 Додати нагадування?",
        reply_markup=reminder_type_keyboard(event_id),
    )


# ── Нагадування ─────────────────────────────────────────────
@router.callback_query(F.data.startswith("rem_"))
async def cb_reminder(cb: CallbackQuery, state: FSMContext) -> None:
    parts = cb.data.split("_")
    rem_type = parts[1]      # 10min / 1hour / 1day / custom
    event_id = int(parts[2])
    uid = cb.from_user.id

    if rem_type == "custom":
        await state.update_data(reminder_event_id=event_id)
        await state.set_state(CreateEvent.reminder_custom)
        await cb.message.edit_text(
            "✏️ Введи кількість хвилин до події для нагадування:\n"
            "<i>Наприклад: 30 (за 30 хвилин), 120 (за 2 години)</i>",
            reply_markup=back_to_main(),
        )
        return

    ev = await event_repo.get_event_by_id(event_id, uid)
    if not ev:
        await cb.message.edit_text("❌ Подію не знайдено.", reply_markup=main_menu())
        await state.clear()
        return

    ok, err = await add_reminder_for_event(
        event_id, uid, ev["event_date"], ev.get("event_time"), rem_type
    )
    if not ok:
        await cb.message.edit_text(f"❌ {err}", reply_markup=main_menu())
    else:
        labels = {"10min": "за 10 хвилин", "1hour": "за 1 годину", "1day": "за 1 день"}
        log_action(uid, "add_reminder", f"event={event_id} type={rem_type}")
        await cb.message.edit_text(
            f"🔔 Нагадування додано — <b>{labels[rem_type]}</b> до події.",
            reply_markup=main_menu(),
        )
    await state.clear()


@router.message(CreateEvent.reminder_custom)
async def fsm_reminder_custom(message: Message, state: FSMContext) -> None:
    text = message.text.strip()
    if not text.isdigit() or int(text) <= 0:
        await message.answer("Введи ціле позитивне число хвилин:")
        return
    minutes = int(text)
    data = await state.get_data()
    event_id = data.get("reminder_event_id") or data.get("last_event_id")
    uid = message.from_user.id
    ev = await event_repo.get_event_by_id(event_id, uid)
    if not ev:
        await message.answer("❌ Подію не знайдено.", reply_markup=main_menu())
        await state.clear()
        return
    ok, err = await add_reminder_for_event(
        event_id, uid, ev["event_date"], ev.get("event_time"), "custom", minutes
    )
    if not ok:
        await message.answer(f"❌ {err}", reply_markup=main_menu())
    else:
        log_action(uid, "add_reminder", f"event={event_id} custom={minutes}min")
        await message.answer(
            f"🔔 Нагадування додано — за <b>{minutes} хвилин</b> до події.",
            reply_markup=main_menu(),
        )
    await state.clear()


# ── Меню нагадувань (окремо від створення події) ─────────────
@router.callback_query(F.data == "reminders_menu")
async def cb_reminders_menu(cb: CallbackQuery, state: FSMContext) -> None:
    uid = cb.from_user.id
    events = await get_all_events(uid)
    if not events:
        await cb.message.edit_text("📭 Немає майбутніх подій.", reply_markup=main_menu())
        return
    await state.set_state(AddReminder.pick_event)
    await cb.message.edit_text(
        "🔔 <b>Додати нагадування</b>\n\nОбери подію:",
        reply_markup=events_list_keyboard(events, "remsel"),
    )


@router.callback_query(F.data.startswith("remsel_"))
async def cb_remsel(cb: CallbackQuery, state: FSMContext) -> None:
    event_id = int(cb.data.split("_")[1])
    await state.clear()
    await cb.message.edit_text(
        "🔔 Обери тип нагадування:",
        reply_markup=reminder_type_keyboard(event_id),
    )


# ── Редагування події ────────────────────────────────────────
@router.callback_query(F.data == "event_edit_menu")
async def cb_edit_menu(cb: CallbackQuery, state: FSMContext) -> None:
    uid = cb.from_user.id
    events = await get_all_events(uid)
    if not events:
        await cb.message.edit_text("📭 Немає майбутніх подій для редагування.", reply_markup=main_menu())
        return
    await state.set_state(EditEvent.pick_event)
    await cb.message.edit_text(
        "✏️ <b>Редагування події</b>\n\nОбери подію для зміни дати/часу:",
        reply_markup=events_list_keyboard(events, "edit"),
    )


@router.callback_query(F.data.startswith("edit_"))
async def cb_edit_pick(cb: CallbackQuery, state: FSMContext) -> None:
    event_id = int(cb.data.split("_")[1])
    await state.update_data(editing_event_id=event_id)
    await state.set_state(EditEvent.date_pick)
    today = date.today()
    await cb.message.edit_text(
        "📆 Обери нову дату події:",
        reply_markup=calendar_keyboard(today.year, today.month),
    )


async def _finish_edit(cb: CallbackQuery, state: FSMContext, time_str) -> None:
    data = await state.get_data()
    uid = cb.from_user.id
    event_id = data["editing_event_id"]
    ok, err = await update_event_datetime(uid, event_id, data["date_str"], time_str)
    if not ok:
        await cb.message.edit_text(f"❌ {err}", reply_markup=main_menu())
    else:
        time_part = f" о {time_str}" if time_str else ""
        log_action(uid, "edit_event", f"id={event_id}")
        await cb.message.edit_text(
            f"✅ Подію оновлено!\n🗓 {data['date_str']}{time_part}",
            reply_markup=main_menu(),
        )
    await state.clear()


# ── Видалення події ──────────────────────────────────────────
@router.callback_query(F.data == "event_delete_menu")
async def cb_delete_menu(cb: CallbackQuery, state: FSMContext) -> None:
    uid = cb.from_user.id
    events = await get_all_events(uid)
    if not events:
        await cb.message.edit_text("📭 Немає подій для видалення.", reply_markup=main_menu())
        return
    await cb.message.edit_text(
        "🗑 <b>Видалення події</b>\n\nОбери подію:",
        reply_markup=events_list_keyboard(events, "del"),
    )


@router.callback_query(F.data.startswith("del_"))
async def cb_del_pick(cb: CallbackQuery, state: FSMContext) -> None:
    event_id = int(cb.data.split("_")[1])
    ev = await event_repo.get_event_by_id(event_id, cb.from_user.id)
    if not ev:
        await cb.message.edit_text("❌ Подію не знайдено.", reply_markup=main_menu())
        return
    await state.update_data(deleting_event_id=event_id)
    await state.set_state(DeleteEvent.confirm)
    d = ev["event_date"].replace("-", ".")
    await cb.message.edit_text(
        f"Ти впевнений, що хочеш видалити:\n\n📅 <b>{ev['title']}</b> ({d})?\n\n"
        "Всі пов'язані нагадування також будуть видалені.",
        reply_markup=confirm_keyboard(f"delconfirm_{event_id}", "menu_main"),
    )


@router.callback_query(F.data.startswith("delconfirm_"))
async def cb_del_confirm(cb: CallbackQuery, state: FSMContext) -> None:
    event_id = int(cb.data.split("_")[1])
    uid = cb.from_user.id
    ok, err = await delete_event(uid, event_id)
    if ok:
        log_action(uid, "delete_event", f"id={event_id}")
        await cb.message.edit_text("✅ Подію видалено.", reply_markup=main_menu())
    else:
        await cb.message.edit_text(f"❌ {err}", reply_markup=main_menu())
    await state.clear()


# ── Довідка ──────────────────────────────────────────────────
@router.callback_query(F.data == "help")
async def cb_help(cb: CallbackQuery) -> None:
    await cb.message.edit_text(
        "📖 <b>Довідка EventBot</b>\n\n"
        "• <b>Створити подію</b> — назва, дата, час (опц.), опис (опц.)\n"
        "• <b>Голосова подія</b> — назва голосом (OpenAI Whisper)\n"
        "• <b>Рекомендації</b> — поради за історією подій (OpenAI GPT)\n"
        "• <b>Нагадування</b> — за 10хв / 1год / 1день / свій час\n"
        "• <b>Перегляд</b> — сьогодні / тиждень / всі майбутні\n"
        "• <b>Редагування</b> — зміна дати та часу події\n"
        "• <b>Видалення</b> — видалення події та її нагадувань\n"
        "• <b>Налаштування</b> — керування акаунтом\n\n"
        "<b>Команди:</b> /today  /week  /all  /help",
        reply_markup=back_to_main(),
    )


# ── Адмін ────────────────────────────────────────────────────
@router.callback_query(F.data == "admin_users")
async def cb_admin_users(cb: CallbackQuery) -> None:
    if cb.from_user.id not in get_admin_ids():
        await cb.answer("⛔ Доступ заборонено.", show_alert=True)
        return
    count = await user_repo.get_users_count()
    updated = await safe_edit_text(
        cb.message,
        f"👥 <b>Зареєстровано користувачів: {count}</b>",
        reply_markup=admin_menu(),
    )
    await cb.answer("Актуально" if not updated else None)


@router.callback_query(F.data == "admin_users_list")
async def cb_admin_users_list(cb: CallbackQuery) -> None:
    if cb.from_user.id not in get_admin_ids():
        await cb.answer("⛔ Доступ заборонено.", show_alert=True)
        return
    users = await user_repo.get_all_users()
    if not users:
        await safe_edit_text(cb.message, "Користувачів ще немає.", reply_markup=admin_menu())
        await cb.answer()
        return
    lines = ["👥 <b>Список користувачів:</b>\n"]
    for u in users:
        uname = f"@{u['username']}" if u.get("username") else "—"
        created = u["created_at"][:10]
        lines.append(f"• {u['full_name']} ({uname}) — {created}")
    text = "\n".join(lines)
    if len(text) > 3800:
        text = text[:3800] + "\n..."
    await safe_edit_text(cb.message, text, reply_markup=admin_menu())
    await cb.answer()


@router.callback_query(F.data == "admin_backup")
async def cb_admin_backup(cb: CallbackQuery) -> None:
    if cb.from_user.id not in get_admin_ids():
        await cb.answer("⛔ Доступ заборонено.", show_alert=True)
        return
    backup_path = DB_PATH.replace(".db", f"_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db")
    shutil.copy2(DB_PATH, backup_path)
    log_action(cb.from_user.id, "admin_backup", backup_path)
    await cb.message.answer_document(
        document=FSInputFile(backup_path, filename=os.path.basename(backup_path)),
        caption=f"💾 Резервна копія БД\n{datetime.now().strftime('%d.%m.%Y %H:%M')}",
    )
    await cb.answer("✅ Резервну копію надіслано.")


@router.callback_query(F.data == "admin_logs")
async def cb_admin_logs(cb: CallbackQuery) -> None:
    if cb.from_user.id not in get_admin_ids():
        await cb.answer("⛔ Доступ заборонено.", show_alert=True)
        return
    log_file = os.path.join(os.path.dirname(__file__), "..", "logs", "actions.log")
    if not os.path.exists(log_file):
        await safe_edit_text(cb.message, "📋 Логів ще немає.", reply_markup=admin_menu())
        await cb.answer()
        return
    with open(log_file, encoding="utf-8") as f:
        lines = f.readlines()
    last = "".join(lines[-50:]) if len(lines) > 50 else "".join(lines)
    if not last:
        await safe_edit_text(cb.message, "📋 Логи порожні.", reply_markup=admin_menu())
        await cb.answer()
        return
    await cb.message.answer(f"📋 <b>Останні 50 дій:</b>\n\n<code>{last[:3800]}</code>")
    await cb.answer()
