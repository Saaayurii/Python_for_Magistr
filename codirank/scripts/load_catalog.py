#!/usr/bin/env python3
"""Load app catalog into database from Google Play CSV and iTunes API."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from db.models import Base
from core.catalog.loader import load_google_play, load_itunes


async def main(csv_path: str | None = None) -> None:
    db_url = "postgresql+asyncpg://user:pass@localhost:5434/codirank"

    engine = create_async_engine(db_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with session_factory() as db:
        if csv_path and Path(csv_path).exists():
            print(f"Loading Google Play apps from {csv_path}...")
            count = await load_google_play(db, csv_path)
            print(f"Loaded {count} Android apps.")
        else:
            print("No Google Play CSV provided or file not found, skipping...")

        print("Fetching iOS apps from iTunes API...")
        count = await load_itunes(db)
        print(f"Loaded {count} iOS apps.")


if __name__ == "__main__":
    csv_path = sys.argv[1] if len(sys.argv) > 1 else None
    asyncio.run(main(csv_path))
