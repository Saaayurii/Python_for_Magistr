from __future__ import annotations

import asyncio
from uuid import UUID

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from states.dialog import DialogStates
from keyboards.inline import app_feedback_keyboard, continue_keyboard
from db.repository import TurnRepo, SessionRepo, AppRepo, FeedbackRepo
from core.llm.client import OllamaClient
from core.llm.embedder import Embedder
from core.codirank.profile import ProfileManager
from core.codirank.attribute_parser import AttributeParser
from core.codirank.ranker import Ranker
from core.codirank.question_gen import QuestionGenerator

router = Router()

ollama = OllamaClient(settings.ollama_url, settings.ollama_model)
embedder = Embedder(ollama)
profile_manager = ProfileManager(settings.profile_alpha)
attr_parser = AttributeParser(ollama)
ranker = Ranker(settings)
question_gen = QuestionGenerator(ollama)


def _format_card(app) -> str:
    platform_str = {"android": "Android", "ios": "iOS", "both": "Android / iOS"}.get(
        app.platform, app.platform
    )
    price_str = "🆓 Бесплатно" if (app.price or 0) == 0 else f"💰 {app.price:.0f}₽"
    ads_str = "❌ Без рекламы" if app.has_ads is False else ("⚠️ Реклама" if app.has_ads else "")
    rating_str = f"⭐ {app.rating:.1f}" if app.rating else ""

    meta_parts = [p for p in [rating_str, price_str, ads_str] if p]
    meta_line = " · ".join(meta_parts)

    store_links = []
    if app.store_url:
        store_links.append(f"[🔗 Магазин]({app.store_url})")

    links_str = " · ".join(store_links) if store_links else ""

    return (
        f"📱 *{app.name}* — {platform_str}\n"
        f"{meta_line}\n\n"
        f"{links_str}"
    )


async def _send_recommendations(message: Message, state: FSMContext, db: AsyncSession) -> None:
    data = await state.get_data()
    session_id = UUID(data["session_id"])

    session_repo = SessionRepo(db)
    session = await session_repo.get_by_id(session_id)
    if session is None or session.profile_vec is None:
        await message.answer("Не удалось получить профиль сессии. Попробуйте /start.")
        return

    import numpy as np
    profile_vec = np.array(session.profile_vec)

    feedback_repo = FeedbackRepo(db)
    rejected_ids = await feedback_repo.get_rejected_ids(session_id)

    candidates = await ranker.get_candidates(db, session_id, profile_vec, excluded_ids=rejected_ids)
    if not candidates:
        await message.answer("😔 Не нашёл подходящих приложений. Попробуйте описать потребность иначе.")
        return

    rejected_embeddings = []
    for app_id in rejected_ids:
        app = await AppRepo(db).get_by_id(app_id)
        if app and app.embedding:
            rejected_embeddings.append(np.array(app.embedding))

    attributes = session.attributes or {}
    top_apps = await ranker.rank(candidates, profile_vec, attributes, rejected_embeddings)

    await state.update_data(
        shown_app_ids=[str(a.id) for a in top_apps],
        candidate_index=0,
    )
    await state.set_state(DialogStates.FEEDBACK)

    await message.answer("🔍 Вот мои рекомендации:")
    for app in top_apps:
        card = _format_card(app)

        history_turns = await TurnRepo(db).get_history(session_id)
        dialog_history = "\n".join(
            f"{'Пользователь' if t.role == 'user' else 'Бот'}: {t.content}"
            for t in history_turns[-6:]
        )
        app_metadata = f"Название: {app.name}, Категория: {app.category}, Описание: {app.description or app.short_desc or ''}"

        try:
            explanation = await ollama.explain_recommendation(
                app_name=app.name,
                dialog_history=dialog_history,
                app_metadata=app_metadata,
            )
            card += f"\n\n_Почему подходит:_ {explanation}"
        except Exception as e:
            logger.warning(f"Failed to generate explanation: {e}")

        await message.answer(card, parse_mode="Markdown", reply_markup=app_feedback_keyboard(str(app.id)))
        await asyncio.sleep(0.5)


@router.message(DialogStates.ELICITING)
async def handle_eliciting(message: Message, state: FSMContext, db: AsyncSession) -> None:
    data = await state.get_data()
    session_id = UUID(data["session_id"])
    turn_count = data.get("turn_count", 0)

    turn_repo = TurnRepo(db)
    session_repo = SessionRepo(db)

    await turn_repo.create(session_id, "user", message.text, None, {})

    try:
        embedding = await embedder.embed(message.text)
    except Exception as e:
        logger.error(f"Embedding error: {e}")
        await message.answer("Что-то пошло не так, попробуйте позже.")
        return

    try:
        parsed_attrs = await attr_parser.parse(message.text)
        sentiment = parsed_attrs.get("sentiment", "neutral")
    except Exception as e:
        logger.warning(f"Attribute parsing error: {e}")
        parsed_attrs = {}
        sentiment = "neutral"

    weight_map = {"positive": 1.0, "neutral": 0.5, "negative": -0.3}
    weight = weight_map.get(sentiment, 0.5)

    try:
        session = await session_repo.get_by_id(session_id)
        import numpy as np
        current_profile = np.array(session.profile_vec) if session.profile_vec else np.zeros(settings.embed_dim)
        new_profile = profile_manager.update(current_profile, embedding, weight)
        profile_norm = profile_manager.norm(new_profile)

        existing_attrs = session.attributes or {}
        merged_attrs = attr_parser.merge(existing_attrs, parsed_attrs)

        await session_repo.update_profile(session_id, new_profile.tolist(), merged_attrs)
    except Exception as e:
        logger.error(f"Profile update error: {e}")
        await message.answer("Что-то пошло не так, попробуйте позже.")
        return

    turn_count += 1
    await state.update_data(turn_count=turn_count)

    force_rank = any(
        kw in message.text.lower()
        for kw in ["хватит", "найди", "покажи", "рекомендуй", "подбери", "предложи"]
    )

    if profile_norm > settings.profile_threshold or force_rank or turn_count >= settings.max_turns_eliciting:
        await state.set_state(DialogStates.RANKING)
        await message.answer("Отлично, ищу подходящие приложения...")
        await _send_recommendations(message, state, db)
    else:
        history_turns = await turn_repo.get_history(session_id)
        dialog_history = "\n".join(
            f"{'Пользователь' if t.role == 'user' else 'Бот'}: {t.content}"
            for t in history_turns[-6:]
        )
        session = await session_repo.get_by_id(session_id)
        known_attributes = session.attributes or {}

        try:
            question = await question_gen.generate(dialog_history, known_attributes)
        except Exception as e:
            logger.warning(f"Question generation error: {e}")
            question = "Расскажите подробнее о ваших предпочтениях?"

        await turn_repo.create(session_id, "bot", question, None, {})
        await message.answer(question)


@router.message(DialogStates.REFINING)
async def handle_refining(message: Message, state: FSMContext, db: AsyncSession) -> None:
    await state.set_state(DialogStates.ELICITING)
    await handle_eliciting(message, state, db)
