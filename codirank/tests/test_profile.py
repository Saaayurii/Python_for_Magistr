from __future__ import annotations

import numpy as np
import pytest

from core.codirank.profile import ProfileManager


def test_update_from_zero():
    pm = ProfileManager(alpha=0.7)
    profile = np.zeros(10)
    embedding = np.ones(10)
    result = pm.update(profile, embedding, weight=1.0)
    expected = 0.7 * np.zeros(10) + 0.3 * np.ones(10)
    np.testing.assert_allclose(result, expected)


def test_update_with_weight():
    pm = ProfileManager(alpha=0.7)
    profile = np.zeros(10)
    embedding = np.ones(10)
    result = pm.update(profile, embedding, weight=0.5)
    expected = 0.7 * np.zeros(10) + 0.3 * np.ones(10) * 0.5
    np.testing.assert_allclose(result, expected)


def test_penalize():
    pm = ProfileManager(alpha=0.7)
    profile = np.ones(10)
    rejected = np.ones(10) * 0.5
    result = pm.penalize(profile, rejected, beta=0.3)
    expected = np.ones(10) - 0.3 * np.ones(10) * 0.5
    np.testing.assert_allclose(result, expected)


def test_norm():
    pm = ProfileManager()
    vec = np.array([3.0, 4.0])
    assert pm.norm(vec) == pytest.approx(5.0)


def test_profile_accumulates():
    pm = ProfileManager(alpha=0.7)
    profile = np.zeros(10)
    for _ in range(5):
        emb = np.ones(10)
        profile = pm.update(profile, emb, weight=1.0)
    assert pm.norm(profile) > 0.1
