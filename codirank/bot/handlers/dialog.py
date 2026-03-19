from __future__ import annotations

import asyncio
from uuid import UUID

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from states.dialog import DialogStates
from keyboards.inline import app_feedback_keyboard, continue_keyboard, platform_selection_keyboard, region_selection_keyboard
from keyboards.reply import main_menu, search_actions, quick_categories
from db.repository import TurnRepo, SessionRepo, AppRepo, FeedbackRepo, UserRepo
from core.llm.client import OllamaClient
from core.llm.embedder import Embedder
from core.codirank.profile import ProfileManager
from core.codirank.attribute_parser import AttributeParser
from core.codirank.ranker import Ranker
from core.codirank.question_gen import QuestionGenerator

router = Router()

# Маппинг кнопок категорий на текстовые запросы
CATEGORY_MAPPING = {
    "🎮 Игры": "Ищу игровое приложение для развлечения",
    "📚 Образование": "Нужно приложение для обучения и образования",
    "💼 Продуктивность": "Требуется приложение для повышения продуктивности и организации работы",
    "🎵 Музыка": "Ищу музыкальное приложение для прослушивания или создания музыки",
    "📸 Фото/Видео": "Нужно приложение для работы с фото и видео",
    "🏋️ Здоровье": "Требуется приложение для здоровья, фитнеса или медицины",
}

ollama = OllamaClient(settings.ollama_url, settings.ollama_model)
embedder = Embedder(ollama)
profile_manager = ProfileManager(settings.profile_alpha)
attr_parser = AttributeParser(ollama)
ranker = Ranker(settings)
question_gen = QuestionGenerator(ollama)


def _format_card(app) -> str:
    """Форматирование красивой карточки приложения"""
    # Определяем платформу с иконкой
    platform_map = {
        "android": "🤖 Android",
        "ios": "🍎 iOS",
        "both": "🤖🍎 Android & iOS"
    }
    platform_str = platform_map.get(app.platform, f"📱 {app.platform}")

    # Цена с красивым форматированием
    if (app.price or 0) == 0:
        price_str = "🆓 <b>Бесплатно</b>"
    else:
        price_str = f"💰 <b>{app.price:.0f}₽</b>"

    # Реклама
    ads_str = ""
    if app.has_ads is False:
        ads_str = "✨ Без рекламы"
    elif app.has_ads is True:
        ads_str = "📢 Есть реклама"

    # Рейтинг с звездами
    rating_str = ""
    if app.rating:
        stars = "⭐" * int(app.rating)
        rating_str = f"{stars} <b>{app.rating:.1f}</b>"

    # Категория
    category_str = f"📂 {app.category}" if app.category else ""

    # Разработчик
    developer_str = f"👨‍💻 {app.developer}" if app.developer else ""

    # Формируем строки метаданных
    meta_lines = []
    if rating_str:
        meta_lines.append(rating_str)
    if category_str:
        meta_lines.append(category_str)

    info_lines = []
    if developer_str:
        info_lines.append(developer_str)
    info_lines.append(price_str)
    if ads_str:
        info_lines.append(ads_str)

    # Описание (первые 150 символов)
    description = ""
    if app.short_desc:
        desc_text = app.short_desc[:150] + "..." if len(app.short_desc) > 150 else app.short_desc
        description = f"\n\n💬 <i>{desc_text}</i>"
    elif app.description:
        desc_text = app.description[:150] + "..." if len(app.description) > 150 else app.description
        description = f"\n\n💬 <i>{desc_text}</i>"

    return (
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📱 <b>{app.name}</b>\n"
        f"{platform_str}\n"
        f"{' • '.join(meta_lines)}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{chr(10).join(info_lines)}"
        f"{description}"
    )


@router.callback_query(F.data.startswith("platform:"))
async def handle_platform_selection(callback: CallbackQuery, state: FSMContext, db: AsyncSession) -> None:
    """Обработка выбора платформы"""
    platform = callback.data.split(":")[1]

    data = await state.get_data()
    session_id = UUID(data["session_id"])

    session_repo = SessionRepo(db)
    session = await session_repo.get_by_id(session_id)

    # Сохраняем платформу в атрибуты сессии
    existing_attrs = session.attributes or {}
    existing_attrs["platform"] = platform

    await session_repo.update_profile(
        session_id,
        session.profile_vec if session.profile_vec is not None else [0.0] * settings.embed_dim,
        existing_attrs
    )

    platform_names = {
        "ios": "🍎 iOS (App Store)",
        "android": "🤖 Android (Google Play)",
        "both": "🤖🍎 Обе платформы"
    }

    await callback.message.edit_text(
        f"✅ Выбрана платформа: <b>{platform_names[platform]}</b>",
        parse_mode="HTML"
    )

    await state.set_state(DialogStates.REGION_SELECTION)

    await callback.message.answer(
        "🌍 <b>Выберите ваш регион:</b>\n\n"
        "Это поможет подобрать приложения на подходящем языке и популярные в вашем регионе",
        parse_mode="HTML",
        reply_markup=region_selection_keyboard()
    )

    await callback.answer()


@router.callback_query(F.data.startswith("region:"))
async def handle_region_selection(callback: CallbackQuery, state: FSMContext, db: AsyncSession) -> None:
    """Обработка выбора региона"""
    region = callback.data.split(":")[1]

    data = await state.get_data()
    session_id = UUID(data["session_id"])

    session_repo = SessionRepo(db)
    session = await session_repo.get_by_id(session_id)

    # Маппинг регионов на языки
    region_to_languages = {
        "ru": ["Russian", "ru"],
        "us": ["English", "en"],
        "eu": ["English", "German", "French", "Spanish", "Italian", "en", "de", "fr", "es", "it"],
        "cn": ["Chinese", "zh"],
        "jp": ["Japanese", "ja"],
        "kr": ["Korean", "ko"],
        "global": None,  # Любые языки
    }

    # Сохраняем регион и предпочтительные языки в атрибуты сессии
    existing_attrs = session.attributes or {}
    existing_attrs["region"] = region

    # Добавляем языки только если это не global
    if region != "global":
        existing_attrs["languages"] = region_to_languages.get(region, [])

    await session_repo.update_profile(
        session_id,
        session.profile_vec if session.profile_vec is not None else [0.0] * settings.embed_dim,
        existing_attrs
    )

    region_names = {
        "ru": "🇷🇺 Россия",
        "us": "🇺🇸 США",
        "eu": "🇪🇺 Европа",
        "cn": "🇨🇳 Китай",
        "jp": "🇯🇵 Япония",
        "kr": "🇰🇷 Корея",
        "global": "🌍 Международный"
    }

    await callback.message.edit_text(
        f"✅ Выбран регион: <b>{region_names[region]}</b>",
        parse_mode="HTML"
    )

    await state.set_state(DialogStates.ELICITING)

    await callback.message.answer(
        "🎯 <b>Отлично! Теперь расскажите, что вы ищете:</b>\n\n"
        "Выберите категорию или опишите своими словами 👇",
        parse_mode="HTML",
        reply_markup=quick_categories()
    )

    await callback.answer()


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

    await message.answer(
        "✨ <b>Вот что я нашел для вас:</b>\n\n"
        "Оцените каждое приложение с помощью кнопок ниже 👇",
        parse_mode="HTML",
        reply_markup=main_menu()
    )

    # Отправляем приложения сразу без объяснений для скорости
    sent_messages = []
    for idx, app in enumerate(top_apps, 1):
        card = _format_card(app)
        sent_msg = await message.answer(
            f"<b>#{idx}</b>\n\n{card}",
            parse_mode="HTML",
            reply_markup=app_feedback_keyboard(str(app.id)),
            disable_web_page_preview=True
        )
        sent_messages.append((sent_msg, app))
        await asyncio.sleep(0.3)

    # Генерируем объяснения в фоне и обновляем сообщения
    async def add_explanations():
        history_turns = await TurnRepo(db).get_history(session_id)
        dialog_history = "\n".join(
            f"{'Пользователь' if t.role == 'user' else 'Бот'}: {t.content}"
            for t in history_turns[-6:]
        )

        for idx, (sent_msg, app) in enumerate(sent_messages, 1):
            try:
                app_metadata = f"Название: {app.name}, Категория: {app.category}, Описание: {app.description or app.short_desc or ''}"
                explanation = await ollama.explain_recommendation(
                    app_name=app.name,
                    dialog_history=dialog_history,
                    app_metadata=app_metadata,
                )

                card = _format_card(app)
                card += f"\n\n💡 <b>Почему подходит:</b>\n<i>{explanation}</i>"

                await sent_msg.edit_text(
                    f"<b>#{idx}</b>\n\n{card}",
                    parse_mode="HTML",
                    reply_markup=app_feedback_keyboard(str(app.id)),
                    disable_web_page_preview=True
                )
            except Exception as e:
                logger.warning(f"Failed to add explanation for {app.name}: {e}")

    # Запускаем генерацию объяснений в фоне (не блокируем пользователя)
    asyncio.create_task(add_explanations())


@router.message(DialogStates.ELICITING, F.text.in_(CATEGORY_MAPPING.keys()))
async def handle_category_button(message: Message, state: FSMContext, db: AsyncSession) -> None:
    """Обработка нажатия кнопки категории"""
    category_text = CATEGORY_MAPPING.get(message.text, message.text)

    # Создаем новое сообщение с текстом категории
    await message.answer(
        f"✅ Выбрана категория: <b>{message.text}</b>\n\n"
        f"Ищу подходящие приложения...",
        parse_mode="HTML",
        reply_markup=search_actions()
    )

    # Обрабатываем category_text вместо message.text
    data = await state.get_data()
    session_id = UUID(data["session_id"])
    turn_count = data.get("turn_count", 0)

    turn_repo = TurnRepo(db)
    session_repo = SessionRepo(db)

    # Используем category_text вместо message.text
    await turn_repo.create(session_id, "user", category_text, None, {})

    try:
        embedding = await embedder.embed(category_text)
    except Exception as e:
        logger.error(f"Embedding error: {e}")
        await message.answer("Что-то пошло не так, попробуйте позже.")
        return

    # Для категорий пропускаем парсинг атрибутов - используем базовые значения
    parsed_attrs = {}
    sentiment = "positive"  # Категории всегда позитивный запрос

    weight_map = {"positive": 1.0, "neutral": 0.5, "negative": -0.3}
    weight = weight_map.get(sentiment, 0.5)

    try:
        session = await session_repo.get_by_id(session_id)
        import numpy as np
        current_profile = np.array(session.profile_vec) if session.profile_vec is not None else np.zeros(settings.embed_dim)
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

    # Для категорий сразу показываем результаты
    await state.set_state(DialogStates.RANKING)
    await message.answer("🔍 Отлично, ищу подходящие приложения...")
    await _send_recommendations(message, state, db)



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
        current_profile = np.array(session.profile_vec) if session.profile_vec is not None else np.zeros(settings.embed_dim)
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


@router.message(F.text == "💬 Другое (ввести текстом)")
async def handle_custom_input(message: Message) -> None:
    """Обработка выбора свободного ввода"""
    await message.answer(
        "✏️ <b>Свободный ввод</b>\n\n"
        "Опишите своими словами, что вы ищете:",
        parse_mode="HTML",
        reply_markup=search_actions()
    )


@router.message(F.text == "✅ Показать результаты")
async def handle_show_results(message: Message, state: FSMContext, db: AsyncSession) -> None:
    """Принудительно показать результаты"""
    data = await state.get_data()
    session_id = data.get("session_id")

    if not session_id:
        await message.answer(
            "❌ Сначала опишите что вы ищете!",
            parse_mode="HTML"
        )
        return

    await state.set_state(DialogStates.RANKING)
    await message.answer("🔍 Ищу подходящие приложения...")
    await _send_recommendations(message, state, db)


@router.callback_query(F.data.startswith("like:"))
async def handle_like(callback: CallbackQuery, state: FSMContext, db: AsyncSession) -> None:
    """Обработка лайка приложения"""
    app_id = callback.data.split(":")[1]

    feedback_repo = FeedbackRepo(db)
    data = await state.get_data()
    session_id = UUID(data["session_id"])

    await feedback_repo.create(session_id, UUID(app_id), "like")

    await callback.answer("✅ Отлично! Рад что понравилось", show_alert=False)
    await callback.message.edit_reply_markup(reply_markup=None)


@router.callback_query(F.data.startswith("dislike:"))
async def handle_dislike(callback: CallbackQuery, state: FSMContext, db: AsyncSession) -> None:
    """Обработка дизлайка приложения"""
    app_id = callback.data.split(":")[1]

    feedback_repo = FeedbackRepo(db)
    data = await state.get_data()
    session_id = UUID(data["session_id"])

    await feedback_repo.create(session_id, UUID(app_id), "dislike")

    await callback.answer("❌ Понял, учту ваши предпочтения", show_alert=False)
    await callback.message.edit_reply_markup(reply_markup=None)


@router.callback_query(F.data.startswith("open:"))
async def handle_open_store(callback: CallbackQuery, db: AsyncSession) -> None:
    """Открыть приложение в магазине"""
    app_id = callback.data.split(":")[1]

    app_repo = AppRepo(db)
    app = await app_repo.get_by_id(UUID(app_id))

    if app and app.store_url:
        await callback.message.answer(
            f"📱 <b>{app.name}</b>\n\n"
            f"🔗 <a href='{app.store_url}'>Открыть в магазине приложений</a>",
            parse_mode="HTML"
        )
        await callback.answer()
    else:
        await callback.answer("❌ Ссылка на магазин недоступна", show_alert=True)


@router.callback_query(F.data.startswith("details:"))
async def handle_details(callback: CallbackQuery, db: AsyncSession) -> None:
    """Показать подробную информацию о приложении"""
    app_id = callback.data.split(":")[1]

    app_repo = AppRepo(db)
    app = await app_repo.get_by_id(UUID(app_id))

    if not app:
        await callback.answer("❌ Приложение не найдено", show_alert=True)
        return

    # Формируем детальную информацию
    details = f"ℹ️ <b>Подробная информация</b>\n\n"
    details += f"📱 <b>Название:</b> {app.name}\n"

    if app.developer:
        details += f"👨‍💻 <b>Разработчик:</b> {app.developer}\n"

    if app.category:
        details += f"📂 <b>Категория:</b> {app.category}\n"

    platform_map = {
        "android": "🤖 Android",
        "ios": "🍎 iOS",
        "both": "🤖🍎 Android & iOS"
    }
    details += f"📲 <b>Платформа:</b> {platform_map.get(app.platform, app.platform)}\n"

    if app.rating:
        details += f"⭐ <b>Рейтинг:</b> {app.rating:.1f}/5.0\n"

    if app.rating_count:
        details += f"👥 <b>Отзывов:</b> {app.rating_count:,}\n"

    price_text = "Бесплатно" if (app.price or 0) == 0 else f"{app.price:.2f}₽"
    details += f"💰 <b>Цена:</b> {price_text}\n"

    if app.has_ads is not None:
        ads_text = "Да" if app.has_ads else "Нет"
        details += f"📢 <b>Реклама:</b> {ads_text}\n"

    if app.has_iap is not None:
        iap_text = "Да" if app.has_iap else "Нет"
        details += f"💳 <b>Встроенные покупки:</b> {iap_text}\n"

    if app.description:
        desc = app.description[:300] + "..." if len(app.description) > 300 else app.description
        details += f"\n📝 <b>Описание:</b>\n{desc}\n"

    if app.store_url:
        details += f"\n<a href='{app.store_url}'>🔗 Открыть в магазине</a>"

    await callback.message.answer(details, parse_mode="HTML", disable_web_page_preview=True)
    await callback.answer()


@router.callback_query(F.data == "find_more")
async def handle_find_more(callback: CallbackQuery, state: FSMContext, db: AsyncSession) -> None:
    """Найти ещё приложения"""
    await callback.message.answer(
        "🔄 <b>Ищу ещё варианты...</b>\n\n"
        "Уточните пожалуйста, что конкретно вам не понравилось в предыдущих вариантах?",
        parse_mode="HTML",
        reply_markup=search_actions()
    )
    await state.set_state(DialogStates.REFINING)
    await callback.answer()


@router.callback_query(F.data == "done")
async def handle_done(callback: CallbackQuery, state: FSMContext, db: AsyncSession) -> None:
    """Завершить поиск"""
    data = await state.get_data()
    session_id = data.get("session_id")

    if session_id:
        session_repo = SessionRepo(db)
        await session_repo.close(session_id)

    await state.clear()

    await callback.message.answer(
        "✅ <b>Спасибо за использование CoDiRank!</b>\n\n"
        "Надеюсь, вы нашли подходящее приложение! 🎉\n\n"
        "Если понадобится помощь снова — просто напишите /start",
        parse_mode="HTML",
        reply_markup=main_menu()
    )
    await callback.answer()


@router.callback_query(F.data == "new_search")
async def handle_new_search_callback(callback: CallbackQuery, state: FSMContext, db: AsyncSession) -> None:
    """Начать новый поиск из callback"""
    session_repo = SessionRepo(db)
    data = await state.get_data()

    if session_id := data.get("session_id"):
        await session_repo.close(session_id)

    await state.clear()

    user_repo = UserRepo(db)
    user = await user_repo.upsert(callback.from_user.id, callback.from_user.username)
    session = await session_repo.create(user.id)

    await state.set_state(DialogStates.ELICITING)
    await state.update_data(
        session_id=str(session.id),
        candidate_index=0,
        candidates=[],
        turn_count=0
    )

    await callback.message.answer(
        "🔄 <b>Начинаем новый поиск!</b>\n\n"
        "Выберите категорию или опишите что ищете:",
        parse_mode="HTML",
        reply_markup=quick_categories()
    )
    await callback.answer()
