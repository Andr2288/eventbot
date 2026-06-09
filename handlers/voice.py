"""Голосове створення подій (OpenAI Whisper)."""

from datetime import date

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from handlers.callbacks import CreateEvent
from handlers.keyboards import back_to_main, calendar_keyboard, main_menu
from services import speech_service
from utils.logger import log_action

router = Router()


@router.callback_query(F.data == "event_create_voice")
async def cb_event_create_voice(cb: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await cb.message.edit_text(
        "🎤 <b>Голосова подія</b>\n\n"
        "Надішли голосове повідомлення з назвою події.\n"
        "Після розпізнавання обереш дату та час як звичайно.",
        reply_markup=back_to_main(),
    )


@router.message(F.voice)
async def handle_voice_message(message: Message, state: FSMContext, bot: Bot) -> None:
    current = await state.get_state()
    if current is not None and not current.startswith("CreateEvent"):
        await message.answer(
            "Заверши поточну дію або повернись у головне меню.",
            reply_markup=main_menu(),
        )
        return

    uid = message.from_user.id
    await message.answer("🎤 Розпізнаю мову…")

    try:
        text = await speech_service.transcribe_telegram_voice(bot, message.voice.file_id)
    except RuntimeError as e:
        await message.answer(f"❌ {e}", reply_markup=main_menu())
        return
    except Exception:
        await message.answer(
            "❌ Не вдалося розпізнати голос. Перевір OPENAI_API_KEY і спробуй ще раз.",
            reply_markup=main_menu(),
        )
        return

    if not text:
        await message.answer("❌ Порожній текст. Спробуй записати голосове ще раз.")
        return

    log_action(uid, "voice_transcribe", text[:80])
    await state.update_data(title=text)
    await state.set_state(CreateEvent.date_pick)
    today = date.today()
    await message.answer(
        f"✅ Розпізнано: <b>{text}</b>\n\n📆 Обери дату події:",
        reply_markup=calendar_keyboard(today.year, today.month),
    )
