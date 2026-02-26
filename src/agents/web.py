# src/agents/web.py
from src.agents.base import BaseAgent
from src.extractors.web_scraper import WebScraper
from src.llm import extract_recipe_from_text
from src.models.recipe import RecipeModel


class WebAgent(BaseAgent):
    def __init__(self):
        self.scraper = WebScraper()

    async def extract(self, url: str) -> RecipeModel:
        text = await self.scraper.scrape(url)
        return extract_recipe_from_text(
            text=text,
            source_url=url,
            source_type="web",
        )
