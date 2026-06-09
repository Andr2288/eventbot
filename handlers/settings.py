"""Налаштування: небезпечні дії з підтвердженням."""

from aiogram import F, Router
from aiogram.types import CallbackQuery

from handlers.keyboards import confirm_keyboard, settings_menu
from services import account_service
from utils.logger import log_action

router = Router()


@router.callback_query(F.data == "settings_menu")
async def cb_settings_menu(cb: CallbackQuery) -> None:
    log_action(cb.from_user.id, "settings_menu")
    await cb.message.edit_text(
        "⚙️ <b>Налаштування</b>\n\nОбери дію. Небезпечні операції потребують підтвердження.",
        reply_markup=settings_menu(),
    )


@router.callback_query(F.data == "settings_del_events")
async def cb_ask_del_events(cb: CallbackQuery) -> None:
    await cb.message.edit_text(
        "Видалити <b>всі</b> події?\n\nЦю дію не можна скасувати.",
        reply_markup=confirm_keyboard("settings_confirm_del_events", "settings_menu"),
    )


@router.callback_query(F.data == "settings_confirm_del_events")
async def cb_confirm_del_events(cb: CallbackQuery) -> None:
    uid = cb.from_user.id
    count = await account_service.delete_all_events(uid)
    log_action(uid, "delete_all_events", f"count={count}")
    await cb.message.edit_text(
        f"✅ Видалено подій: <b>{count}</b>.",
        reply_markup=settings_menu(),
    )


@router.callback_query(F.data == "settings_clear_reminders")
async def cb_ask_clear_reminders(cb: CallbackQuery) -> None:
    await cb.message.edit_text(
        "Очистити <b>всі</b> нагадування?\n\nПодії залишаться.",
        reply_markup=confirm_keyboard("settings_confirm_clear_reminders", "settings_menu"),
    )


@router.callback_query(F.data == "settings_confirm_clear_reminders")
async def cb_confirm_clear_reminders(cb: CallbackQuery) -> None:
    uid = cb.from_user.id
    count = await account_service.clear_all_reminders(uid)
    log_action(uid, "clear_all_reminders", f"count={count}")
    await cb.message.edit_text(
        f"✅ Видалено нагадувань: <b>{count}</b>.",
        reply_markup=settings_menu(),
    )


@router.callback_query(F.data == "settings_del_account")
async def cb_ask_del_account(cb: CallbackQuery) -> None:
    await cb.message.edit_text(
        "Видалити <b>акаунт</b> і всі дані?\n\nПотрібно буде знову натиснути /start.",
        reply_markup=confirm_keyboard("settings_confirm_del_account", "settings_menu"),
    )


@router.callback_query(F.data == "settings_confirm_del_account")
async def cb_confirm_del_account(cb: CallbackQuery) -> None:
    uid = cb.from_user.id
    await account_service.delete_account(uid)
    log_action(uid, "delete_account")
    await cb.message.edit_text(
        "✅ Акаунт видалено.\n\nНатисни /start, щоб зареєструватись знову.",
    )
