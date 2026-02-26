# src/agents/instagram.py
import asyncio

from src.agents.base import BaseAgent
from src.extractors.instagram_loader import InstagramExtractor
from src.llm import extract_recipe_from_images, extract_recipe_from_text
from src.models.recipe import RecipeModel


class InstagramAgent(BaseAgent):
    def __init__(self):
        self.extractor = InstagramExtractor()

    async def extract(self, url: str) -> RecipeModel:
        extracted = await asyncio.to_thread(self.extractor.extract, url)
        text = extracted["text"]
        images = extracted["images"]

        if images:
            return extract_recipe_from_images(
                images=images,
                caption=text,
                source_url=url,
                source_type="instagram",
            )

        return extract_recipe_from_text(
            text=text,
            source_url=url,
            source_type="instagram",
        )
