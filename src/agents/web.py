# src/agents/web.py
"""Agente de extração para páginas web genéricas.

Delega ao `WebScraper` a obtenção de múltiplas fontes (conteúdo da página + JSON-LD)
e envia ao LLM para extração estruturada.
"""
from src.agents.base import BaseAgent, format_sources
from src.extractors.web_scraper import WebScraper
from src.llm import extract_recipe_from_text
from src.models.recipe import RecipeModel


class WebAgent(BaseAgent):
    def __init__(self):
        self.scraper = WebScraper()

    async def extract(self, url: str) -> list[RecipeModel]:
        sources = await self.scraper.scrape_sources(url)
        text = format_sources(sources)
        return await extract_recipe_from_text(
            text=text,
            source_url=url,
            source_type="web",
        )
