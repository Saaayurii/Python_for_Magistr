from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .models import Base

_engine = None
async_session_factory: async_sessionmaker[AsyncSession] = None  # type: ignore


async def init_db(database_url: str | None = None) -> None:
    global _engine, async_session_factory

    if database_url is None:
        from config import settings  # type: ignore[import]  # bot/ dir is on PYTHONPATH
        database_url = settings.database_url

    _engine = create_async_engine(database_url, echo=False)
    async_session_factory = async_sessionmaker(_engine, expire_on_commit=False)

    async with _engine.begin() as conn:
        # Create pgvector extension first
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
