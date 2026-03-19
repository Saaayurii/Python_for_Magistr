from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from states.dialog import DialogStates
from db.repository import UserRepo, SessionRepo

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext, db: AsyncSession) -> None:
    user_repo = UserRepo(db)
    session_repo = SessionRepo(db)

    user = await user_repo.upsert(message.from_user.id, message.from_user.username)
    session = await session_repo.create(user.id)

    await state.set_state(DialogStates.ELICITING)
    await state.update_data(session_id=str(session.id), candidate_index=0, candidates=[])

    logger.info(f"User {user.id} started new session {session.id}")

    await message.answer(
        "👋 Привет! Я помогу подобрать мобильное приложение под ваши потребности.\n\n"
        "Расскажите, что вы ищете? Опишите своими словами — для чего вам нужно приложение, "
        "что важно: цена, платформа, наличие рекламы?"
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(
        "🤖 *CoDiRank — помощник по подбору приложений*\n\n"
        "Просто опишите, что вам нужно — я задам пару уточняющих вопросов "
        "и подберу подходящие приложения.\n\n"
        "Команды:\n"
        "/start — начать поиск\n"
        "/new — начать новый поиск\n"
        "/help — эта справка",
        parse_mode="Markdown",
    )


@router.message(Command("new"))
async def cmd_new(message: Message, state: FSMContext, db: AsyncSession) -> None:
    session_repo = SessionRepo(db)
    data = await state.get_data()

    if session_id := data.get("session_id"):
        await session_repo.close(session_id)

    await state.clear()

    user_repo = UserRepo(db)
    user = await user_repo.upsert(message.from_user.id, message.from_user.username)
    session = await session_repo.create(user.id)

    await state.set_state(DialogStates.ELICITING)
    await state.update_data(session_id=str(session.id), candidate_index=0, candidates=[])

    await message.answer("🔄 Начинаем новый поиск!\n\nЧто вы ищете на этот раз?")
