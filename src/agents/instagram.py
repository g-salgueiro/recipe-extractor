# src/agents/instagram.py
"""Agente de extração para posts e reels do Instagram.

Delega ao `InstagramExtractor` a obtenção do conteúdo (fontes nomeadas e/ou imagens).
A rota LLM depende do que foi retornado:
  - Se há imagens → `extract_recipe_from_images` (visão LLM)
  - Caso contrário → `extract_recipe_from_text`
"""
import asyncio

from src.agents.base import BaseAgent, format_sources
from src.extractors.instagram_loader import InstagramExtractor
from src.llm import extract_recipe_from_images, extract_recipe_from_text
from src.models.recipe import RecipeModel


class InstagramAgent(BaseAgent):
    def __init__(self):
        self.extractor = InstagramExtractor()

    async def extract(self, url: str) -> list[RecipeModel]:
        extracted = await asyncio.to_thread(self.extractor.extract, url)
        sources = extracted["sources"]
        images = extracted["images"]

        if images:
            caption = format_sources(sources)
            return await extract_recipe_from_images(
                images=images,
                caption=caption,
                source_url=url,
                source_type="instagram",
            )

        text = format_sources(sources)
        return await extract_recipe_from_text(
            text=text,
            source_url=url,
            source_type="instagram",
        )
