from __future__ import annotations

from core.codirank.attribute_parser import AttributeParser
from core.codirank.profile import ProfileManager
from core.codirank.question_gen import QuestionGenerator
from core.codirank.ranker import Ranker
from core.llm.client import OllamaClient
from core.llm.embedder import Embedder


class CoDiRankEngine:
    def __init__(self, settings) -> None:
        self.client = OllamaClient(settings.ollama_url, settings.ollama_model)
        self.embedder = Embedder(self.client)
        self.profile_manager = ProfileManager(settings.profile_alpha)
        self.attr_parser = AttributeParser(self.client)
        self.ranker = Ranker(settings)
        self.question_gen = QuestionGenerator(self.client)
