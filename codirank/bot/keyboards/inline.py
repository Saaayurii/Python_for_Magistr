from __future__ import annotations
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def app_feedback_keyboard(app_id: str) -> InlineKeyboardMarkup:
    """Клавиатура для оценки приложения"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Подходит", callback_data=f"like:{app_id}"),
        InlineKeyboardButton(text="❌ Не то", callback_data=f"dislike:{app_id}"),
    )
    builder.row(
        InlineKeyboardButton(text="📱 Открыть в магазине", callback_data=f"open:{app_id}"),
    )
    builder.row(
        InlineKeyboardButton(text="ℹ️ Подробная информация", callback_data=f"details:{app_id}"),
    )
    return builder.as_markup()


def continue_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура продолжения поиска"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔄 Показать ещё варианты", callback_data="find_more"),
    )
    builder.row(
        InlineKeyboardButton(text="✅ Спасибо, достаточно", callback_data="done"),
        InlineKeyboardButton(text="🔍 Новый поиск", callback_data="new_search"),
    )
    return builder.as_markup()


def loading_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура во время загрузки"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="⏳ Поиск...", callback_data="loading"),
    )
    return builder.as_markup()


def platform_selection_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора платформы"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🍎 iOS (App Store)", callback_data="platform:ios"),
        InlineKeyboardButton(text="🤖 Android (Google Play)", callback_data="platform:android"),
    )
    builder.row(
        InlineKeyboardButton(text="🤖🍎 Обе платформы", callback_data="platform:both"),
    )
    return builder.as_markup()


def region_selection_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора региона"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🇷🇺 Россия", callback_data="region:ru"),
        InlineKeyboardButton(text="🇺🇸 США", callback_data="region:us"),
    )
    builder.row(
        InlineKeyboardButton(text="🇪🇺 Европа", callback_data="region:eu"),
        InlineKeyboardButton(text="🇨🇳 Китай", callback_data="region:cn"),
    )
    builder.row(
        InlineKeyboardButton(text="🇯🇵 Япония", callback_data="region:jp"),
        InlineKeyboardButton(text="🇰🇷 Корея", callback_data="region:kr"),
    )
    builder.row(
        InlineKeyboardButton(text="🌍 Международный", callback_data="region:global"),
    )
    return builder.as_markup()
