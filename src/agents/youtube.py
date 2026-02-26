# src/agents/youtube.py
"""Agente de extração para vídeos do YouTube.

Delega a obtenção do texto ao `YouTubeExtractor`, que tenta três estratégias
em ordem: API de legendas → descrição do vídeo → Whisper. O texto resultante
é enviado ao LLM para extração estruturada.
"""
from src.agents.base import BaseAgent
from src.extractors.youtube_transcript import YouTubeExtractor
from src.llm import extract_recipe_from_text
from src.models.recipe import RecipeModel


class YouTubeAgent(BaseAgent):
    def __init__(self):
        self.extractor = YouTubeExtractor()

    async def extract(self, url: str) -> list[RecipeModel]:
        text = await self.extractor.extract_text(url)
        return await extract_recipe_from_text(
            text=text,
            source_url=url,
            source_type="youtube",
        )
