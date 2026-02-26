# src/agents/youtube.py
from src.agents.base import BaseAgent
from src.extractors.youtube_transcript import YouTubeExtractor
from src.llm import extract_recipe_from_text
from src.models.recipe import RecipeModel


class YouTubeAgent(BaseAgent):
    def __init__(self):
        self.extractor = YouTubeExtractor()

    async def extract(self, url: str) -> RecipeModel:
        text = await self.extractor.extract_text(url)
        return extract_recipe_from_text(
            text=text,
            source_url=url,
            source_type="youtube",
        )
