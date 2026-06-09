"""Статистика та графіки."""

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, FSInputFile

from handlers.keyboards import stats_menu
from handlers.ui import edit_or_answer
from services import stats_service
from utils.logger import log_action

router = Router()


@router.callback_query(F.data == "stats_menu")
async def cb_stats_menu(cb: CallbackQuery) -> None:
    await edit_or_answer(
        cb,
        "📊 <b>Статистика</b>\n\nОбери період:",
        reply_markup=stats_menu(),
    )


@router.callback_query(F.data.in_({"stats_week", "stats_month"}))
async def cb_stats_period(cb: CallbackQuery) -> None:
    uid = cb.from_user.id
    days = 7 if cb.data == "stats_week" else 30
    period = "тиждень" if days == 7 else "місяць"

    await edit_or_answer(cb, f"📊 Генерую графік за {period}…")

    path = await stats_service.generate_stats_image(uid, days)
    if not path:
        await edit_or_answer(
            cb,
            f"📭 Немає подій за {period}.",
            reply_markup=stats_menu(),
        )
        return

    try:
        log_action(uid, "stats", f"days={days}")
        if cb.message.text is not None:
            try:
                await cb.message.delete()
            except TelegramBadRequest:
                pass
        await cb.message.answer_photo(
            photo=FSInputFile(path),
            caption=f"📊 Статистика за {period} ({days} дн.)",
            reply_markup=stats_menu(),
        )
    finally:
        if path.exists():
            path.unlink()
