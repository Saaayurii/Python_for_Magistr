from __future__ import annotations

from core.llm.client import OllamaClient


class AttributeParser:
    def __init__(self, client: OllamaClient) -> None:
        self.client = client

    async def parse(self, text: str) -> dict:
        return await self.client.extract_attributes(text)

    def merge(self, existing: dict, new: dict) -> dict:
        result = dict(existing)
        for key, value in new.items():
            if value is None:
                continue
            if isinstance(value, list):
                existing_list = result.get(key, []) or []
                merged = list(set(existing_list) | set(value))
                result[key] = merged
            else:
                result[key] = value
        return result
