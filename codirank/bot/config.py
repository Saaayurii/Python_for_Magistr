from __future__ import annotations
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    bot_token: str
    database_url: str
    ollama_url: str = "http://ollama:11434"
    ollama_model: str = "qwen2.5:7b-instruct-q4_K_M"
    embed_dim: int = 3584

    profile_alpha: float = 0.7
    profile_threshold: float = 0.3
    reject_beta: float = 0.3
    rank_beta1: float = 0.5
    rank_beta2: float = 0.35
    rank_beta3: float = 0.15
    top_k_candidates: int = 50
    top_k_results: int = 3

    max_turns_eliciting: int = 6
    max_clarify_questions: int = 3

    class Config:
        env_file = ".env"


settings = Settings()
