from __future__ import annotations

import asyncio
import json
from typing import Any

import httpx
import numpy as np
from loguru import logger

from .prompts import (
    ATTRIBUTE_EXTRACTION_PROMPT,
    CLARIFY_PROMPT_TEMPLATE,
    EXPLANATION_PROMPT_TEMPLATE,
)

MAX_RETRIES = 3
RETRY_DELAY = 1.0


class OllamaClient:
    def __init__(self, base_url: str, model: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._client = httpx.AsyncClient(timeout=120.0)

    async def _post_with_retry(self, endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.base_url}{endpoint}"
        for attempt in range(MAX_RETRIES):
            try:
                response = await self._client.post(url, json=payload)
                response.raise_for_status()
                return response.json()
            except httpx.TimeoutException as e:
                if attempt < MAX_RETRIES - 1:
                    delay = RETRY_DELAY * (2 ** attempt)
                    logger.warning(f"Timeout on {endpoint}, retry {attempt+1} in {delay}s")
                    await asyncio.sleep(delay)
                else:
                    raise
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error on {endpoint}: {e.response.status_code}")
                raise

    async def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 512,
    ) -> str:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        data = await self._post_with_retry("/api/chat", payload)
        return data["message"]["content"]

    async def embed(self, text: str) -> np.ndarray:
        payload = {"model": self.model, "prompt": text}
        data = await self._post_with_retry("/api/embeddings", payload)
        return np.array(data["embedding"], dtype=np.float32)

    async def embed_batch(self, texts: list[str]) -> list[np.ndarray]:
        results = []
        for text in texts:
            emb = await self.embed(text)
            results.append(emb)
        return results

    async def extract_attributes(self, text: str) -> dict:
        messages = [
            {"role": "system", "content": ATTRIBUTE_EXTRACTION_PROMPT},
            {"role": "user", "content": text},
        ]
        raw = await self.chat(messages, temperature=0.05, max_tokens=256)
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw)

    async def generate_question(self, dialog_history: str, known_attributes: str) -> str:
        prompt = CLARIFY_PROMPT_TEMPLATE.format(
            dialog_history=dialog_history,
            known_attributes=known_attributes,
        )
        messages = [{"role": "user", "content": prompt}]
        return await self.chat(messages, temperature=0.7, max_tokens=150)

    async def explain_recommendation(
        self, app_name: str, dialog_history: str, app_metadata: str
    ) -> str:
        prompt = EXPLANATION_PROMPT_TEMPLATE.format(
            app_name=app_name,
            dialog_history=dialog_history,
            app_metadata=app_metadata,
        )
        messages = [{"role": "user", "content": prompt}]
        # Оптимизировано для скорости: меньше токенов и температура
        return await self.chat(messages, temperature=0.3, max_tokens=80)

    async def close(self) -> None:
        await self._client.aclose()
