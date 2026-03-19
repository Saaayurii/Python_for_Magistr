from __future__ import annotations

import numpy as np
import pytest

from core.codirank.ranker import Ranker, cosine_similarity


class FakeSettings:
    rank_beta1 = 0.5
    rank_beta2 = 0.35
    rank_beta3 = 0.15
    top_k_candidates = 50
    top_k_results = 3


class FakeApp:
    def __init__(self, name, embedding, category=None, platform="android", price=0, has_ads=None, has_iap=None, languages=None):
        self.id = name
        self.name = name
        self.embedding = embedding
        self.category = category
        self.platform = platform
        self.price = price
        self.has_ads = has_ads
        self.has_iap = has_iap
        self.languages = languages


def test_cosine_similarity_identical():
    a = np.array([1.0, 0.0, 0.0])
    assert cosine_similarity(a, a) == pytest.approx(1.0)


def test_cosine_similarity_orthogonal():
    a = np.array([1.0, 0.0])
    b = np.array([0.0, 1.0])
    assert cosine_similarity(a, b) == pytest.approx(0.0)


def test_cosine_similarity_zero_vector():
    a = np.zeros(5)
    b = np.ones(5)
    assert cosine_similarity(a, b) == 0.0


def test_score_returns_float():
    ranker = Ranker(FakeSettings())
    emb = np.array([1.0, 0.0, 0.0])
    app = FakeApp("TestApp", emb.tolist())
    score = ranker.score(app, emb, {}, [])
    assert isinstance(score, float)


def test_score_higher_for_matching_attributes():
    ranker = Ranker(FakeSettings())
    emb = np.array([1.0, 0.0, 0.0])
    app_match = FakeApp("Match", emb.tolist(), category="games", platform="android", price=0)
    app_nomatch = FakeApp("NoMatch", emb.tolist(), category="finance", platform="ios", price=9.99)

    attrs = {"category": "games", "platform": "android", "monetization": "free_only"}
    score_match = ranker.score(app_match, emb, attrs, [])
    score_nomatch = ranker.score(app_nomatch, emb, attrs, [])
    assert score_match > score_nomatch


def test_rank_returns_top_k():
    ranker = Ranker(FakeSettings())
    profile = np.array([1.0, 0.0, 0.0])
    apps = [
        FakeApp(f"App{i}", np.random.rand(3).tolist())
        for i in range(10)
    ]
    top = asyncio.run(_async_rank(ranker, apps, profile))
    assert len(top) <= FakeSettings.top_k_results


import asyncio

async def _async_rank(ranker, apps, profile):
    return await ranker.rank(apps, profile, {}, [])
