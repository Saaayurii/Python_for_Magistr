from __future__ import annotations

import asyncio
from loguru import logger
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import settings
from handlers import start, dialog, feedback
from middlewares.db import DatabaseMiddleware
from db import init_db


async def main() -> None:
    logger.info("Starting CoDiRank bot...")

    await init_db()

    bot = Bot(token=settings.bot_token)
    dp = Dispatcher(storage=MemoryStorage())

    dp.update.middleware(DatabaseMiddleware())

    dp.include_router(start.router)
    dp.include_router(feedback.router)
    dp.include_router(dialog.router)

    logger.info("Bot started, polling...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
