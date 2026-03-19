from __future__ import annotations

import numpy as np


class ProfileManager:
    def __init__(self, alpha: float = 0.7) -> None:
        self.alpha = alpha

    def update(
        self,
        current_profile: np.ndarray,
        new_embedding: np.ndarray,
        weight: float = 1.0,
    ) -> np.ndarray:
        """P(t) = alpha * P(t-1) + (1 - alpha) * E(a_t) * w(a_t)"""
        return self.alpha * current_profile + (1 - self.alpha) * new_embedding * weight

    def penalize(
        self,
        current_profile: np.ndarray,
        rejected_embedding: np.ndarray,
        beta: float = 0.3,
    ) -> np.ndarray:
        """P(t) = P(t) - beta * E(m_rejected)"""
        return current_profile - beta * rejected_embedding

    def norm(self, profile_vec: np.ndarray) -> float:
        """L2-норма вектора"""
        return float(np.linalg.norm(profile_vec))
