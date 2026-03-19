from __future__ import annotations

import asyncio
from pathlib import Path
from loguru import logger
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import FSInputFile

from config import settings
from handlers import start, dialog, feedback
from middlewares.db import DatabaseMiddleware
from db import init_db


async def check_bot_avatar(bot: Bot) -> None:
    """Проверка и информация об аватарке бота"""
    avatar_path = Path(__file__).parent / "public" / "cat.jpeg"

    logger.info("=" * 60)
    logger.info("BOT AVATAR SETUP INSTRUCTIONS")
    logger.info("=" * 60)
    logger.info(f"Avatar file location: {avatar_path.absolute()}")

    if avatar_path.exists():
        logger.info("✓ Avatar file found")
        logger.info("\nTo set bot avatar:")
        logger.info("1. Open @BotFather in Telegram")
        logger.info("2. Send /mybots")
        logger.info("3. Select your bot")
        logger.info("4. Choose 'Edit Bot'")
        logger.info("5. Choose 'Edit Botpic'")
        logger.info(f"6. Upload the file: {avatar_path.absolute()}")
    else:
        logger.warning("✗ Avatar file not found!")
    logger.info("=" * 60)


async def main() -> None:
    logger.info("Starting CoDiRank bot...")

    await init_db()

    bot = Bot(token=settings.bot_token)
    dp = Dispatcher(storage=MemoryStorage())

    dp.update.middleware(DatabaseMiddleware())

    dp.include_router(start.router)
    dp.include_router(feedback.router)
    dp.include_router(dialog.router)

    # Проверка аватарки бота
    await check_bot_avatar(bot)

    logger.info("Bot started, polling...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
