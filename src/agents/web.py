# src/agents/web.py
"""Agente de extração para páginas web genéricas.

Delega ao `WebScraper` a obtenção do conteúdo textual da página
(httpx → Playwright como fallback para sites com JS pesado) e envia
o texto ao LLM para extração estruturada.
"""
from src.agents.base import BaseAgent
from src.extractors.web_scraper import WebScraper
from src.llm import extract_recipe_from_text
from src.models.recipe import RecipeModel


class WebAgent(BaseAgent):
    def __init__(self):
        self.scraper = WebScraper()

    async def extract(self, url: str) -> list[RecipeModel]:
        text = await self.scraper.scrape(url)
        return await extract_recipe_from_text(
            text=text,
            source_url=url,
            source_type="web",
        )
