from __future__ import annotations

import json
from core.llm.client import OllamaClient


class QuestionGenerator:
    def __init__(self, client: OllamaClient) -> None:
        self.client = client

    async def generate(self, dialog_history: str, known_attributes: dict) -> str:
        attrs_str = json.dumps(known_attributes, ensure_ascii=False)
        return await self.client.generate_question(dialog_history, attrs_str)
