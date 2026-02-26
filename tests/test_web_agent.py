# tests/test_web_agent.py
import pytest
from unittest.mock import AsyncMock, patch

from src.agents.web import WebAgent
from src.models.recipe import Ingredient, RecipeModel


@pytest.fixture
def mock_recipe():
    return RecipeModel(
        title="Bolo",
        ingredients=[Ingredient(name="farinha")],
        steps=["Passo 1"],
        extraction_confidence=0.9,
        source_url="https://example.com/receita",
        source_type="web",
    )


@pytest.mark.asyncio
async def test_web_agent_extract_returns_recipe(mock_recipe):
    agent = WebAgent()
    url = "https://example.com/receita"

    with patch.object(agent.scraper, "scrape", new_callable=AsyncMock, return_value="Texto da receita..."):
        with patch("src.agents.web.extract_recipe_from_text", return_value=mock_recipe):
            result = await agent.extract(url)

    assert isinstance(result, RecipeModel)
    assert result.source_type == "web"


@pytest.mark.asyncio
async def test_web_agent_passes_correct_args(mock_recipe):
    agent = WebAgent()
    url = "https://example.com/receita"

    with patch.object(agent.scraper, "scrape", new_callable=AsyncMock, return_value="texto"):
        with patch("src.agents.web.extract_recipe_from_text", return_value=mock_recipe) as mock_fn:
            await agent.extract(url)

    _, kwargs = mock_fn.call_args
    assert kwargs["source_url"] == url
    assert kwargs["source_type"] == "web"
