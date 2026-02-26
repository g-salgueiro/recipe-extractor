# src/agents/base.py
from abc import ABC, abstractmethod

from src.models.recipe import RecipeModel


class BaseAgent(ABC):
    @abstractmethod
    async def extract(self, url: str) -> RecipeModel:
        """Extrai a receita da URL fornecida."""
        ...
