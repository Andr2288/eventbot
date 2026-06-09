"""Рекомендації (OpenAI GPT)."""

from aiogram import F, Router
from aiogram.types import CallbackQuery

from handlers.keyboards import back_to_main
from services import recommend_service
from utils.logger import log_action

router = Router()


@router.callback_query(F.data == "recommendations")
async def cb_recommendations(cb: CallbackQuery) -> None:
    uid = cb.from_user.id
    await cb.message.edit_text("💡 <b>Формую рекомендації…</b>")

    try:
        text = await recommend_service.get_recommendations(uid)
    except RuntimeError as e:
        await cb.message.edit_text(f"❌ {e}", reply_markup=back_to_main())
        return
    except Exception:
        await cb.message.edit_text(
            "❌ Не вдалося отримати рекомендації. Перевір OPENAI_API_KEY.",
            reply_markup=back_to_main(),
        )
        return

    log_action(uid, "recommendations")
    await cb.message.edit_text(
        f"💡 <b>Рекомендації</b>\n\n{text}",
        reply_markup=back_to_main(),
    )
