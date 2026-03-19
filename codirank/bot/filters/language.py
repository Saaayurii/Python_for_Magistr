from __future__ import annotations
from aiogram.filters import BaseFilter
from aiogram.types import Message


class RussianOrEnglishFilter(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        return message.text is not None and len(message.text.strip()) > 0
