from __future__ import annotations

from uuid import UUID

import numpy as np
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from states.dialog import DialogStates
from keyboards.inline import continue_keyboard
from db.repository import FeedbackRepo, AppRepo, SessionRepo
from core.codirank.profile import ProfileManager

router = Router()
profile_manager = ProfileManager(settings.profile_alpha)


@router.callback_query(F.data.startswith("like:"))
async def handle_like(callback: CallbackQuery, state: FSMContext, db: AsyncSession) -> None:
    app_id = UUID(callback.data.split(":")[1])
    data = await state.get_data()
    session_id = UUID(data["session_id"])

    await FeedbackRepo(db).create(session_id, app_id, "like")
    await callback.answer("👍 Отлично!")
    await callback.message.reply(
        "Рад помочь! Хотите найти ещё приложения?",
        reply_markup=continue_keyboard(),
    )


@router.callback_query(F.data.startswith("dislike:"))
async def handle_dislike(callback: CallbackQuery, state: FSMContext, db: AsyncSession) -> None:
    app_id = UUID(callback.data.split(":")[1])
    data = await state.get_data()
    session_id = UUID(data["session_id"])

    feedback_repo = FeedbackRepo(db)
    await feedback_repo.create(session_id, app_id, "dislike")

    app_repo = AppRepo(db)
    app = await app_repo.get_by_id(app_id)

    if app and app.embedding:
        session_repo = SessionRepo(db)
        session = await session_repo.get_by_id(session_id)
        current_profile = np.array(session.profile_vec) if session.profile_vec else np.zeros(settings.embed_dim)
        app_emb = np.array(app.embedding)
        new_profile = profile_manager.penalize(current_profile, app_emb, settings.reject_beta)
        await session_repo.update_profile(session_id, new_profile.tolist(), session.attributes or {})

    await callback.answer("👎 Понял, запомнил!")
    await callback.message.reply(
        "Понял, это не подходит. Опишите подробнее, что не так — я учту это в следующих рекомендациях.",
    )
    await state.set_state(DialogStates.REFINING)


@router.callback_query(F.data.startswith("details:"))
async def handle_details(callback: CallbackQuery, db: AsyncSession) -> None:
    app_id = UUID(callback.data.split(":")[1])
    app = await AppRepo(db).get_by_id(app_id)

    if not app:
        await callback.answer("Приложение не найдено")
        return

    details = (
        f"📱 *{app.name}*\n"
        f"Разработчик: {app.developer or 'N/A'}\n"
        f"Категория: {app.category or 'N/A'}\n"
        f"Рейтинг: {app.rating or 'N/A'}\n"
        f"Цена: {'Бесплатно' if (app.price or 0) == 0 else f'{app.price:.2f}₽'}\n"
        f"Платформа: {app.platform}\n\n"
        f"{app.description or app.short_desc or 'Описание недоступно'}"
    )
    await callback.answer()
    await callback.message.reply(details[:4096], parse_mode="Markdown")


@router.callback_query(F.data == "find_more")
async def handle_find_more(callback: CallbackQuery, state: FSMContext, db: AsyncSession) -> None:
    await callback.answer()
    await state.set_state(DialogStates.REFINING)
    await callback.message.reply("Хорошо! Уточните, что хотите найти дополнительно?")


@router.callback_query(F.data == "done")
async def handle_done(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    await callback.message.reply(
        "✅ Отлично! Рад был помочь. Когда понадобится ещё — просто напишите /start."
    )
