from __future__ import annotations

import uuid
from typing import List
from uuid import UUID

import numpy as np
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from .models import App, Feedback, Session, Turn, User


class UserRepo:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def upsert(self, user_id: int, username: str | None) -> User:
        stmt = (
            insert(User)
            .values(id=user_id, username=username)
            .on_conflict_do_update(index_elements=["id"], set_={"username": username})
            .returning(User)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one()


class SessionRepo:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, user_id: int) -> Session:
        session = Session(user_id=user_id)
        self.db.add(session)
        await self.db.flush()
        return session

    async def get_by_id(self, session_id: UUID) -> Session | None:
        result = await self.db.execute(select(Session).where(Session.id == session_id))
        return result.scalar_one_or_none()

    async def get_active(self, user_id: int) -> Session | None:
        result = await self.db.execute(
            select(Session)
            .where(Session.user_id == user_id, Session.status == "active")
            .order_by(Session.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def update_profile(
        self, session_id: UUID, vec: list[float], attributes: dict
    ) -> None:
        await self.db.execute(
            update(Session)
            .where(Session.id == session_id)
            .values(profile_vec=vec, attributes=attributes)
        )

    async def close(self, session_id: str) -> None:
        await self.db.execute(
            update(Session)
            .where(Session.id == UUID(session_id))
            .values(status="completed")
        )


class TurnRepo:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self,
        session_id: UUID,
        role: str,
        content: str,
        embedding: list[float] | None,
        attributes: dict,
    ) -> Turn:
        result = await self.db.execute(
            select(Turn)
            .where(Turn.session_id == session_id)
            .order_by(Turn.turn_index.desc())
            .limit(1)
        )
        last = result.scalar_one_or_none()
        turn_index = (last.turn_index + 1) if last else 0

        turn = Turn(
            session_id=session_id,
            turn_index=turn_index,
            role=role,
            content=content,
            embedding=embedding,
            attributes=attributes,
        )
        self.db.add(turn)
        await self.db.flush()
        return turn

    async def get_history(self, session_id: UUID) -> List[Turn]:
        result = await self.db.execute(
            select(Turn)
            .where(Turn.session_id == session_id)
            .order_by(Turn.turn_index)
        )
        return list(result.scalars().all())


class AppRepo:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def nearest(
        self,
        embedding: list[float],
        limit: int = 50,
        exclude_ids: list[UUID] | None = None,
    ) -> List[App]:
        query = select(App).where(App.embedding.is_not(None))
        if exclude_ids:
            query = query.where(App.id.not_in(exclude_ids))
        query = query.order_by(App.embedding.op("<=>")(embedding)).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_by_id(self, app_id: UUID) -> App | None:
        result = await self.db.execute(select(App).where(App.id == app_id))
        return result.scalar_one_or_none()


class FeedbackRepo:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, session_id: UUID, app_id: UUID, signal: str) -> Feedback:
        fb = Feedback(session_id=session_id, app_id=app_id, signal=signal)
        self.db.add(fb)
        await self.db.flush()
        return fb

    async def get_rejected_ids(self, session_id: UUID) -> List[UUID]:
        result = await self.db.execute(
            select(Feedback.app_id).where(
                Feedback.session_id == session_id,
                Feedback.signal == "dislike",
            )
        )
        return list(result.scalars().all())
