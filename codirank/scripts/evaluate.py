#!/usr/bin/env python3
"""
Offline evaluation of CoDiRank algorithm.

Simulates user queries and measures Precision@K and NDCG@K
by checking if returned apps match the requested category.
Compares CoDiRank (semantic + attr + penalty) vs pure cosine baseline.
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from db.models import App
from core.llm.client import OllamaClient
from core.codirank.ranker import Ranker, cosine_similarity

DB_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5434/codirank")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")

# Test queries: (natural language query, expected category keyword)
TEST_QUERIES = [
    ("I need a fitness app to track workouts and calories", "Health & Fitness"),
    ("Looking for a photo editing app", "Photo & Video"),
    ("Need a budgeting app to manage my finances", "Finance"),
    ("I want a music streaming app", "Music"),
    ("Looking for a navigation app with offline maps", "Navigation"),
    ("I need a productivity app for task management", "Productivity"),
    ("Want a weather forecast app", "Weather"),
    ("Looking for a food delivery or restaurant app", "Food & Drink"),
    ("Need an educational app for learning languages", "Education"),
    ("I want a social networking app", "Social Networking"),
]

TOP_K = 5


class SimpleSettings:
    rank_beta1 = 0.5
    rank_beta2 = 0.35
    rank_beta3 = 0.15
    top_k_candidates = 50
    top_k_results = TOP_K


def dcg(relevances: list[float]) -> float:
    return sum(rel / np.log2(i + 2) for i, rel in enumerate(relevances))


def ndcg(relevances: list[float], k: int) -> float:
    ideal = sorted(relevances, reverse=True)[:k]
    ideal_dcg = dcg(ideal)
    if ideal_dcg == 0:
        return 0.0
    return dcg(relevances[:k]) / ideal_dcg


def precision_at_k(relevances: list[float], k: int) -> float:
    return sum(1 for r in relevances[:k] if r > 0) / k


async def get_top_cosine(
    apps: list[App], query_emb: np.ndarray, k: int
) -> list[App]:
    scored = []
    for app in apps:
        if app.embedding is None:
            continue
        sim = cosine_similarity(np.array(app.embedding), query_emb)
        scored.append((app, sim))
    scored.sort(key=lambda x: x[1], reverse=True)
    return [a for a, _ in scored[:k]]


async def evaluate() -> None:
    engine = create_async_engine(DB_URL)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    client = OllamaClient(OLLAMA_URL, OLLAMA_MODEL)
    ranker = Ranker(SimpleSettings())

    async with session_factory() as db:
        result = await db.execute(select(App).where(App.embedding.is_not(None)))
        all_apps = list(result.scalars().all())

    print(f"Loaded {len(all_apps)} apps with embeddings")
    print("=" * 60)
    print(f"{'Query':<50} {'P@K':>6} {'P@K(base)':>9} {'NDCG':>6} {'NDCG(base)':>10}")
    print("-" * 60)

    codirank_precisions = []
    baseline_precisions = []
    codirank_ndcgs = []
    baseline_ndcgs = []

    for query, expected_category in TEST_QUERIES:
        query_emb = await client.embed(query)

        # CoDiRank: nearest candidates via cosine, then re-rank
        # Get top-50 by cosine
        candidates = await get_top_cosine(all_apps, query_emb, 50)
        attrs = {"category": expected_category}
        top_codirank = await ranker.rank(candidates, query_emb, attrs, [])

        # Baseline: pure cosine top-K
        top_baseline = await get_top_cosine(all_apps, query_emb, TOP_K)

        def relevance(app: App) -> float:
            if app.category and expected_category.lower() in app.category.lower():
                return 1.0
            return 0.0

        rel_codirank = [relevance(a) for a in top_codirank]
        rel_baseline = [relevance(a) for a in top_baseline]

        p_codirank = precision_at_k(rel_codirank, TOP_K)
        p_baseline = precision_at_k(rel_baseline, TOP_K)
        n_codirank = ndcg(rel_codirank, TOP_K)
        n_baseline = ndcg(rel_baseline, TOP_K)

        codirank_precisions.append(p_codirank)
        baseline_precisions.append(p_baseline)
        codirank_ndcgs.append(n_codirank)
        baseline_ndcgs.append(n_baseline)

        query_short = query[:48] + ".." if len(query) > 50 else query
        print(f"{query_short:<50} {p_codirank:>6.2f} {p_baseline:>9.2f} {n_codirank:>6.3f} {n_baseline:>10.3f}")

    print("=" * 60)
    print(f"{'AVERAGE':<50} {sum(codirank_precisions)/len(codirank_precisions):>6.2f} "
          f"{sum(baseline_precisions)/len(baseline_precisions):>9.2f} "
          f"{sum(codirank_ndcgs)/len(codirank_ndcgs):>6.3f} "
          f"{sum(baseline_ndcgs)/len(baseline_ndcgs):>10.3f}")
    print()
    print(f"CoDiRank  Precision@{TOP_K}: {sum(codirank_precisions)/len(codirank_precisions):.4f}")
    print(f"Baseline  Precision@{TOP_K}: {sum(baseline_precisions)/len(baseline_precisions):.4f}")
    print(f"CoDiRank  NDCG@{TOP_K}:      {sum(codirank_ndcgs)/len(codirank_ndcgs):.4f}")
    print(f"Baseline  NDCG@{TOP_K}:      {sum(baseline_ndcgs)/len(baseline_ndcgs):.4f}")

    await client.close()


if __name__ == "__main__":
    asyncio.run(evaluate())
