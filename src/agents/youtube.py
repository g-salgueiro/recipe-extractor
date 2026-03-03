# src/agents/youtube.py
"""Agente de extração para vídeos do YouTube.

Delega a obtenção de múltiplas fontes ao `YouTubeExtractor` (legenda + descrição +
título), formata como seções rotuladas e envia ao LLM para extração estruturada.
"""
from src.agents.base import BaseAgent, format_sources
from src.extractors.youtube_transcript import YouTubeExtractor
from src.llm import extract_recipe_from_text
from src.models.recipe import RecipeModel


class YouTubeAgent(BaseAgent):
    def __init__(self):
        self.extractor = YouTubeExtractor()

    async def extract(self, url: str) -> list[RecipeModel]:
        sources = await self.extractor.extract_sources(url)
        text = format_sources(sources)
        return await extract_recipe_from_text(
            text=text,
            source_url=url,
            source_type="youtube",
        )
