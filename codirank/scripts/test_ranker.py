#!/usr/bin/env python3
"""Manual test for the CoDiRank ranker."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from db.models import Base
from core.llm.client import OllamaClient
from core.codirank.profile import ProfileManager
from core.codirank.ranker import Ranker


OLLAMA_URL = "http://localhost:11434"
OLLAMA_MODEL = "qwen2.5:7b-instruct-q4_K_M"
DB_URL = "postgresql+asyncpg://user:pass@localhost:5434/codirank"


class FakeSettings:
    ollama_url = OLLAMA_URL
    ollama_model = OLLAMA_MODEL
    profile_alpha = 0.7
    profile_threshold = 0.3
    reject_beta = 0.3
    rank_beta1 = 0.5
    rank_beta2 = 0.35
    rank_beta3 = 0.15
    top_k_candidates = 50
    top_k_results = 5
    embed_dim = 3584


async def main() -> None:
    engine = create_async_engine(DB_URL)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    client = OllamaClient(OLLAMA_URL, OLLAMA_MODEL)
    profile_mgr = ProfileManager(alpha=0.7)
    settings = FakeSettings()
    ranker = Ranker(settings)

    test_queries = [
        "Хочу приложение для медитации, бесплатное, без рекламы, для iOS",
        "Ищу игру-головоломку на Android",
        "Нужен трекер питания для похудения",
    ]

    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"Query: {query}")
        print("="*60)

        emb = await client.embed(query)
        profile = profile_mgr.update(np.zeros(settings.embed_dim), emb, weight=1.0)

        async with session_factory() as db:
            candidates = await ranker.get_candidates(db, None, profile)
            if not candidates:
                print("No candidates found (DB may be empty)")
                continue
            top = await ranker.rank(candidates, profile, {}, [])
            for i, app in enumerate(top, 1):
                print(f"{i}. {app.name} ({app.platform}) - {app.category}")

    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
