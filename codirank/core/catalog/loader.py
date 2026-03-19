from __future__ import annotations

from pathlib import Path

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import App
from .sources import fetch_itunes_apps, parse_google_play_csv


def _make_upsert(app_data: dict):
    """Build upsert statement using __table__ to avoid SQLAlchemy MetaData name conflict."""
    tbl = App.__table__
    stmt = (
        insert(tbl)
        .values(app_data)
        .on_conflict_do_update(
            index_elements=["external_id"],
            set_={k: v for k, v in app_data.items() if k != "external_id"},
        )
    )
    return stmt


async def load_google_play(db: AsyncSession, csv_path: str | Path) -> int:
    count = 0
    for app_data in parse_google_play_csv(csv_path):
        await db.execute(_make_upsert(app_data))
        count += 1
        if count % 500 == 0:
            await db.commit()
            print(f"  Loaded {count} Android apps...")
    await db.commit()
    return count


async def load_itunes(db: AsyncSession) -> int:
    apps = await fetch_itunes_apps()
    count = 0
    for app_data in apps:
        if not app_data["name"] or not app_data["store_url"]:
            continue
        await db.execute(_make_upsert(app_data))
        count += 1
    await db.commit()
    return count
