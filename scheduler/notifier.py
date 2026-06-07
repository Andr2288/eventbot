"""Планувальник автоматичних нагадувань."""

import asyncio
import logging
from datetime import datetime

from aiogram import Bot

import db.reminder_repo as reminder_repo
from utils.logger import log_action

logger = logging.getLogger(__name__)

CHECK_INTERVAL = 30  # секунд між перевірками


async def check_and_send(bot: Bot) -> None:
    """Перевірити нагадування та надіслати ті, час яких настав."""
    now = datetime.now()
    due = await reminder_repo.get_due_reminders(now)

    for rem in due:
        user_id  = rem["user_id"]
        title    = rem["title"]
        ev_date  = datetime.strptime(rem["event_date"], "%Y-%m-%d").strftime("%d.%m.%Y")
        ev_time  = rem.get("event_time")
        desc     = rem.get("description")
        rem_type = rem.get("reminder_type", "custom")

        time_part = f" о <b>{ev_time}</b>" if ev_time else ""
        desc_part = f"\n📝 {desc}" if desc else ""

        labels = {
            "10min": "⏰ За 10 хвилин",
            "1hour": "🕐 За 1 годину",
            "1day":  "📅 Завтра",
            "custom": "🔔 Нагадування",
        }
        label = labels.get(rem_type, "🔔 Нагадування")

        text = (
            f"{label}\n\n"
            f"📅 <b>{title}</b>\n"
            f"🗓 {ev_date}{time_part}"
            f"{desc_part}"
        )

        try:
            await bot.send_message(chat_id=user_id, text=text)
            await reminder_repo.mark_sent(rem["id"])
            log_action(user_id, "reminder_sent", f"event={rem['event_id']} type={rem_type}")
            logger.info("Нагадування надіслано: user=%s event=%s", user_id, rem["event_id"])
        except Exception as e:
            logger.warning("Помилка надсилання user=%s: %s", user_id, e)


async def run_scheduler(bot: Bot) -> None:
    """Нескінченний цикл планувальника."""
    logger.info("Планувальник запущено. Інтервал: %s сек.", CHECK_INTERVAL)
    await asyncio.sleep(5)  # пауза при старті
    while True:
        try:
            await check_and_send(bot)
        except asyncio.CancelledError:
            logger.info("Планувальник зупинено.")
            break
        except Exception as e:
            logger.error("Помилка планувальника: %s", e)
        await asyncio.sleep(CHECK_INTERVAL)
