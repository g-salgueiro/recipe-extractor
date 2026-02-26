# src/agents/base.py
"""Interface abstrata para agentes de extração de receitas.

Cada fonte (YouTube, Instagram, Web) possui um agente concreto que implementa
`extract()`. O agente coordena o extractor da fonte com a camada LLM e devolve
uma lista de receitas — um único conteúdo pode conter múltiplas.
"""
from abc import ABC, abstractmethod

from src.models.recipe import RecipeModel


class BaseAgent(ABC):
    @abstractmethod
    async def extract(self, url: str) -> list[RecipeModel]:
        """Extrai todas as receitas da URL fornecida."""
        ...
