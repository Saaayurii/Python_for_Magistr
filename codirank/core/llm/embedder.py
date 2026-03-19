from __future__ import annotations

import numpy as np
from .client import OllamaClient


class Embedder:
    def __init__(self, client: OllamaClient) -> None:
        self.client = client

    async def embed(self, text: str) -> np.ndarray:
        return await self.client.embed(text)

    async def embed_batch(self, texts: list[str]) -> list[np.ndarray]:
        return await self.client.embed_batch(texts)
