from __future__ import annotations

from aiogram import Router, F
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from states.dialog import DialogStates
from db.repository import UserRepo, SessionRepo
from keyboards.reply import main_menu, quick_categories
from keyboards.inline import platform_selection_keyboard

router = Router()


WELCOME_MESSAGE = """🌟 <b>Добро пожаловать в CoDiRank!</b> 🌟

Я — умный помощник по подбору мобильных приложений.
Помогу найти идеальное приложение для ваших задач! 📱✨

<b>🎯 Как я работаю:</b>
1️⃣ Расскажите, что вам нужно
2️⃣ Отвечу на пару уточняющих вопросов
3️⃣ Подберу лучшие приложения персонально для вас

<b>💡 Примеры запросов:</b>
• "Нужен органайзер для работы без рекламы"
• "Ищу игру-головоломку для Android"
• "Приложение для изучения языков бесплатно"

Готовы начать? Выберите категорию или опишите своими словами! 👇"""


HELP_MESSAGE = """📚 <b>Справка по CoDiRank</b>

<b>🤖 О боте:</b>
Я использую искусственный интеллект для анализа ваших предпочтений и подбора идеальных приложений.

<b>⚡️ Команды:</b>
/start — начать работу
/new — новый поиск
/help — эта справка

<b>💬 Советы:</b>
• Описывайте детально что нужно
• Указывайте платформу (iOS/Android)
• Скажите, важна ли цена и реклама
• Можете использовать кнопки для быстрого выбора

<b>❓ Возникли вопросы?</b>
Просто напишите мне, я всегда готов помочь! 😊"""


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, db: AsyncSession) -> None:
    user_repo = UserRepo(db)
    session_repo = SessionRepo(db)

    user = await user_repo.upsert(message.from_user.id, message.from_user.username)
    session = await session_repo.create(user.id)

    await state.set_state(DialogStates.PLATFORM_SELECTION)
    await state.update_data(
        session_id=str(session.id),
        candidate_index=0,
        candidates=[],
        turn_count=0
    )

    logger.info(f"User {user.id} started new session {session.id}")

    await message.answer(
        WELCOME_MESSAGE,
        parse_mode="HTML",
        reply_markup=main_menu()
    )

    await message.answer(
        "📱 <b>Выберите платформу:</b>\n\n"
        "Для какой операционной системы вы ищете приложения?",
        parse_mode="HTML",
        reply_markup=platform_selection_keyboard()
    )


@router.message(Command("help"))
@router.message(F.text == "❓ Помощь")
async def cmd_help(message: Message) -> None:
    await message.answer(
        HELP_MESSAGE,
        parse_mode="HTML",
        reply_markup=main_menu()
    )


@router.message(Command("new"))
@router.message(F.text == "🔄 Новый поиск")
@router.message(F.text == "🔄 Начать заново")
async def cmd_new(message: Message, state: FSMContext, db: AsyncSession) -> None:
    session_repo = SessionRepo(db)
    data = await state.get_data()

    if session_id := data.get("session_id"):
        await session_repo.close(session_id)

    await state.clear()

    user_repo = UserRepo(db)
    user = await user_repo.upsert(message.from_user.id, message.from_user.username)
    session = await session_repo.create(user.id)

    await state.set_state(DialogStates.PLATFORM_SELECTION)
    await state.update_data(
        session_id=str(session.id),
        candidate_index=0,
        candidates=[],
        turn_count=0
    )

    await message.answer(
        "🔄 <b>Начинаем новый поиск!</b>\n\n"
        "📱 Выберите платформу:",
        parse_mode="HTML",
        reply_markup=platform_selection_keyboard()
    )


@router.message(F.text == "🔍 Найти приложение")
async def cmd_search(message: Message, state: FSMContext, db: AsyncSession) -> None:
    """Обработчик кнопки 'Найти приложение'"""
    data = await state.get_data()

    if not data.get("session_id"):
        # Если нет активной сессии, создаем новую
        await cmd_new(message, state, db)
    else:
        current_state = await state.get_state()
        if current_state == DialogStates.PLATFORM_SELECTION:
            await message.answer(
                "⚠️ Сначала выберите платформу:",
                parse_mode="HTML",
                reply_markup=platform_selection_keyboard()
            )
        else:
            await message.answer(
                "🔍 <b>Поиск приложения</b>\n\n"
                "Выберите категорию или опишите что вам нужно:",
                parse_mode="HTML",
                reply_markup=quick_categories()
            )
