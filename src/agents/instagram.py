# src/agents/instagram.py
"""Agente de extração para posts e reels do Instagram.

Delega ao `InstagramExtractor` a obtenção do conteúdo (texto e/ou imagens).
A rota LLM depende do que foi retornado:
  - Se há imagens → `extract_recipe_from_images` (visão LLM)
  - Caso contrário → `extract_recipe_from_text`

O `InstagramExtractor` encapsula toda a lógica de fallback:
instaloader → og:description + yt-dlp + Whisper. Esse agente apenas
decide qual função LLM acionar com base no resultado.
"""
import asyncio

from src.agents.base import BaseAgent
from src.extractors.instagram_loader import InstagramExtractor
from src.llm import extract_recipe_from_images, extract_recipe_from_text
from src.models.recipe import RecipeModel


class InstagramAgent(BaseAgent):
    def __init__(self):
        self.extractor = InstagramExtractor()

    async def extract(self, url: str) -> list[RecipeModel]:
        # InstagramExtractor é síncrono (usa instaloader/yt-dlp/whisper),
        # por isso é executado em thread para não bloquear o event loop.
        extracted = await asyncio.to_thread(self.extractor.extract, url)
        text = extracted["text"]
        images = extracted["images"]

        if images:
            return await extract_recipe_from_images(
                images=images,
                caption=text,
                source_url=url,
                source_type="instagram",
            )

        return await extract_recipe_from_text(
            text=text,
            source_url=url,
            source_type="instagram",
        )
