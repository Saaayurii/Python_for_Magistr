from __future__ import annotations
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def app_feedback_keyboard(app_id: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="👍 Подходит", callback_data=f"like:{app_id}"),
        InlineKeyboardButton(text="👎 Не то", callback_data=f"dislike:{app_id}"),
        InlineKeyboardButton(text="📋 Подробнее", callback_data=f"details:{app_id}"),
    )
    return builder.as_markup()


def continue_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔄 Найти ещё", callback_data="find_more"),
        InlineKeyboardButton(text="✅ Достаточно", callback_data="done"),
    )
    return builder.as_markup()
