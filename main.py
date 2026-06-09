"""EventBot — Telegram-бот для управління подіями та нагадуваннями."""

import asyncio
import logging
import os
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from utils.env import load_env

load_env()

from db.database import init_db
from handlers import commands, callbacks, recommendations, registration, settings, voice
from middleware.auth import RegisteredUserMiddleware
from scheduler.notifier import run_scheduler

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def main() -> None:
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN не знайдено у .env файлі")

    await init_db()
    logger.info("База даних ініціалізована.")

    bot = Bot(
        token=token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    dp.message.middleware(RegisteredUserMiddleware())
    dp.callback_query.middleware(RegisteredUserMiddleware())

    dp.include_router(registration.router)
    dp.include_router(commands.router)
    dp.include_router(callbacks.router)
    dp.include_router(voice.router)
    dp.include_router(recommendations.router)
    dp.include_router(settings.router)

    # Запуск планувальника нагадувань
    asyncio.create_task(run_scheduler(bot))
    logger.info("Планувальник нагадувань запущено.")

    logger.info("EventBot запущено.")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
