#!/usr/bin/env python3
"""Analyze catalog composition and print statistics."""
from __future__ import annotations

import asyncio
import os
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from db.models import App

DB_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5434/codirank")


async def main() -> None:
    engine = create_async_engine(DB_URL)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as db:
        result = await db.execute(select(App))
        apps = list(result.scalars().all())

    total = len(apps)
    with_embedding = sum(1 for a in apps if a.embedding is not None)

    print("=" * 60)
    print("CATALOG STATISTICS")
    print("=" * 60)
    print(f"Total apps:        {total}")
    print(f"With embeddings:   {with_embedding} ({with_embedding/total*100:.1f}%)")

    # Platform
    platforms = Counter(a.platform for a in apps)
    print("\n--- Platform ---")
    for platform, cnt in platforms.most_common():
        print(f"  {platform:10s}: {cnt:5d} ({cnt/total*100:.1f}%)")

    # Category
    categories = Counter(a.category for a in apps if a.category)
    print("\n--- Top 20 Categories ---")
    for cat, cnt in categories.most_common(20):
        print(f"  {cat:30s}: {cnt:5d} ({cnt/total*100:.1f}%)")

    # Price
    free = sum(1 for a in apps if (a.price or 0) == 0)
    paid = total - free
    print("\n--- Monetization ---")
    print(f"  Free:   {free:5d} ({free/total*100:.1f}%)")
    print(f"  Paid:   {paid:5d} ({paid/total*100:.1f}%)")

    # IAP / Ads
    has_iap = sum(1 for a in apps if a.has_iap is True)
    has_ads = sum(1 for a in apps if a.has_ads is True)
    print(f"  Has IAP: {has_iap:5d} ({has_iap/total*100:.1f}%)")
    print(f"  Has Ads: {has_ads:5d} ({has_ads/total*100:.1f}%)")

    # Rating
    rated = [a for a in apps if a.rating is not None]
    if rated:
        avg_rating = sum(float(a.rating) for a in rated) / len(rated)
        print(f"\n--- Ratings ---")
        print(f"  Apps with rating: {len(rated):5d} ({len(rated)/total*100:.1f}%)")
        print(f"  Average rating:   {avg_rating:.2f}")

    # Languages
    lang_counter: Counter = Counter()
    for a in apps:
        if a.languages:
            for lang in a.languages:
                lang_counter[lang] += 1
    if lang_counter:
        print("\n--- Top 15 Languages ---")
        for lang, cnt in lang_counter.most_common(15):
            print(f"  {lang:20s}: {cnt:5d}")

    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
