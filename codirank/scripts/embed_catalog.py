#!/usr/bin/env python3
"""Pre-compute embeddings for all apps in the catalog."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from tqdm import tqdm

from db.models import App
from core.llm.client import OllamaClient


OLLAMA_URL = "http://localhost:11434"
OLLAMA_MODEL = "qwen2.5:7b-instruct-q4_K_M"
DB_URL = "postgresql+asyncpg://user:pass@localhost:5434/codirank"
BATCH_SIZE = 32


async def main() -> None:
    engine = create_async_engine(DB_URL)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    client = OllamaClient(OLLAMA_URL, OLLAMA_MODEL)

    async with session_factory() as db:
        result = await db.execute(select(App).where(App.embedding.is_(None)))
        apps = list(result.scalars().all())

    print(f"Found {len(apps)} apps without embeddings")

    for i in tqdm(range(0, len(apps), BATCH_SIZE), desc="Embedding apps"):
        batch = apps[i : i + BATCH_SIZE]
        texts = [
            f"{app.name}. {app.category or ''}. {(app.short_desc or app.description or '')[:500]}"
            for app in batch
        ]
        try:
            embeddings = await client.embed_batch(texts)
        except Exception as e:
            print(f"Error embedding batch {i}: {e}")
            continue

        async with session_factory() as db:
            for app, emb in zip(batch, embeddings):
                await db.execute(
                    update(App).where(App.id == app.id).values(embedding=emb.tolist())
                )
            await db.commit()

    await client.close()
    print("Done!")


if __name__ == "__main__":
    asyncio.run(main())
