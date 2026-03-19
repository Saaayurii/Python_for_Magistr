from __future__ import annotations
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder


def main_menu() -> ReplyKeyboardMarkup:
    """Главное меню с основными командами"""
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="🔍 Найти приложение"),
        KeyboardButton(text="❓ Помощь"),
    )
    builder.row(
        KeyboardButton(text="🔄 Новый поиск"),
        KeyboardButton(text="📊 Мои рекомендации"),
    )
    return builder.as_markup(resize_keyboard=True)


def search_actions() -> ReplyKeyboardMarkup:
    """Действия во время поиска"""
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="✅ Показать результаты"),
    )
    builder.row(
        KeyboardButton(text="🔄 Начать заново"),
        KeyboardButton(text="❌ Отмена"),
    )
    return builder.as_markup(resize_keyboard=True)


def quick_categories() -> ReplyKeyboardMarkup:
    """Быстрый выбор категорий"""
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="🎮 Игры"),
        KeyboardButton(text="📚 Образование"),
    )
    builder.row(
        KeyboardButton(text="💼 Продуктивность"),
        KeyboardButton(text="🎵 Музыка"),
    )
    builder.row(
        KeyboardButton(text="📸 Фото/Видео"),
        KeyboardButton(text="🏋️ Здоровье"),
    )
    builder.row(
        KeyboardButton(text="💬 Другое (ввести текстом)"),
    )
    return builder.as_markup(resize_keyboard=True)
