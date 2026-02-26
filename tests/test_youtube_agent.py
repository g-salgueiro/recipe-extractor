# tests/test_youtube_agent.py
"""Testes unitários do YouTubeAgent.

Usa AsyncMock para simular `extract_text` (extractor) e `extract_recipe_from_text`
(LLM). Verifica que o agente passa os parâmetros corretos (source_url, source_type).
"""
import pytest
from unittest.mock import AsyncMock, patch

from src.agents.youtube import YouTubeAgent
from src.models.recipe import Ingredient, RecipeModel


@pytest.fixture
def mock_recipe():
    return RecipeModel(
        title="Bolo de Chocolate",
        ingredients=[Ingredient(name="farinha", quantity="2", unit="xícaras")],
        steps=["Passo 1"],
        extraction_confidence=0.9,
        source_url="https://youtube.com/watch?v=abc",
        source_type="youtube",
    )


@pytest.mark.asyncio
async def test_youtube_agent_extract_returns_recipe(mock_recipe):
    agent = YouTubeAgent()
    with patch.object(agent.extractor, "extract_text", new_callable=AsyncMock, return_value="texto da receita"):
        with patch("src.agents.youtube.extract_recipe_from_text", new_callable=AsyncMock, return_value=[mock_recipe]):
            result = await agent.extract("https://youtube.com/watch?v=abc")

    assert isinstance(result, list)
    assert result[0].source_type == "youtube"
    assert result[0].title == "Bolo de Chocolate"


@pytest.mark.asyncio
async def test_youtube_agent_passes_correct_source_type(mock_recipe):
    agent = YouTubeAgent()
    url = "https://youtube.com/watch?v=abc"
    with patch.object(agent.extractor, "extract_text", new_callable=AsyncMock, return_value="texto"):
        with patch("src.agents.youtube.extract_recipe_from_text", new_callable=AsyncMock, return_value=[mock_recipe]) as mock_fn:
            await agent.extract(url)

    _, kwargs = mock_fn.call_args
    assert kwargs["source_type"] == "youtube"
    assert kwargs["source_url"] == url
