from __future__ import annotations

from typing import TYPE_CHECKING, Any, List
from uuid import UUID

import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import App
from db.repository import AppRepo, FeedbackRepo

if TYPE_CHECKING:
    from bot.config import Settings


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


class Ranker:
    def __init__(self, settings: Any) -> None:
        self.settings = settings

    async def get_candidates(
        self,
        db: AsyncSession,
        session_id: UUID,
        profile_vec: np.ndarray,
        excluded_ids: list[UUID] | None = None,
    ) -> List[App]:
        app_repo = AppRepo(db)
        return await app_repo.nearest(
            profile_vec.tolist(),
            limit=self.settings.top_k_candidates,
            exclude_ids=excluded_ids or [],
        )

    def _attr_match(self, app: App, attributes: dict) -> float:
        if not attributes:
            return 0.5

        total = 0
        matched = 0

        cat = attributes.get("category")
        if cat:
            total += 1
            if app.category and cat.lower() in app.category.lower():
                matched += 1

        monetization = attributes.get("monetization")
        if monetization and monetization != "any":
            total += 1
            if monetization == "free_only" and (app.price or 0) == 0:
                matched += 1
            elif monetization == "paid_ok":
                matched += 1

        has_ads = attributes.get("has_ads")
        if has_ads is not None:
            total += 1
            if app.has_ads == has_ads:
                matched += 1

        has_iap = attributes.get("has_iap")
        if has_iap is not None:
            total += 1
            if app.has_iap == has_iap:
                matched += 1

        platform = attributes.get("platform")
        if platform and platform != "any":
            total += 1
            if app.platform == platform or app.platform == "both":
                matched += 1

        languages = attributes.get("languages")
        if languages:
            total += 2  # Увеличиваем вес языка (2 вместо 1)
            if app.languages:
                # Проверяем совпадение языков (учитываем как полные названия, так и коды)
                app_langs_lower = [lang.lower() for lang in app.languages]
                user_langs_lower = [lang.lower() for lang in languages]

                matched_count = sum(
                    1 for user_lang in user_langs_lower
                    if any(user_lang in app_lang or app_lang in user_lang for app_lang in app_langs_lower)
                )

                if matched_count > 0:
                    matched += 2  # Полное совпадение языка
                elif any(lang.lower() in ["english", "en"] for lang in app.languages):
                    matched += 1  # Частичное совпадение (английский как универсальный)

        region = attributes.get("region")
        if region and region != "global":
            # Регион уже учтен через languages, но добавляем небольшой бонус
            # для приложений с правильной локализацией
            total += 1
            if languages and app.languages:
                app_langs_lower = [lang.lower() for lang in app.languages]
                user_langs_lower = [lang.lower() for lang in languages]
                if any(user_lang in app_lang or app_lang in user_lang
                       for user_lang in user_langs_lower
                       for app_lang in app_langs_lower):
                    matched += 1

        if total == 0:
            return 0.5
        return matched / total

    def _reject_penalty(self, app_emb: np.ndarray, rejected_embs: list[np.ndarray]) -> float:
        if not rejected_embs:
            return 0.0
        similarities = [cosine_similarity(app_emb, rej) for rej in rejected_embs]
        return max(similarities)

    def score(
        self,
        app: App,
        profile_vec: np.ndarray,
        attributes: dict,
        rejected_embeddings: list[np.ndarray],
    ) -> float:
        if app.embedding is None:
            return -1.0

        app_emb = np.array(app.embedding)
        semantic = cosine_similarity(app_emb, profile_vec)
        attr = self._attr_match(app, attributes)
        penalty = self._reject_penalty(app_emb, rejected_embeddings)

        return (
            self.settings.rank_beta1 * semantic
            + self.settings.rank_beta2 * attr
            - self.settings.rank_beta3 * penalty
        )

    async def rank(
        self,
        candidates: List[App],
        profile_vec: np.ndarray,
        attributes: dict,
        rejected_embeddings: list[np.ndarray],
    ) -> List[App]:
        scored = [
            (app, self.score(app, profile_vec, attributes, rejected_embeddings))
            for app in candidates
        ]
        scored.sort(key=lambda x: x[1], reverse=True)
        return [app for app, _ in scored[: self.settings.top_k_results]]
