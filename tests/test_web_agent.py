# tests/test_web_agent.py
"""Testes unitários do WebAgent.

Usa AsyncMock para simular `scraper.scrape_sources` e `extract_recipe_from_text`.
Verifica retorno de lista, propagação correta de source_url/source_type,
e formatação de múltiplas fontes via format_sources.
"""
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

    with patch.object(agent.scraper, "scrape_sources", new_callable=AsyncMock, return_value={"conteudo_pagina": "Texto da receita..."}):
        with patch("src.agents.web.extract_recipe_from_text", new_callable=AsyncMock, return_value=[mock_recipe]):
            result = await agent.extract(url)

    assert isinstance(result, list)
    assert result[0].source_type == "web"


@pytest.mark.asyncio
async def test_web_agent_passes_correct_args(mock_recipe):
    agent = WebAgent()
    url = "https://example.com/receita"

    with patch.object(agent.scraper, "scrape_sources", new_callable=AsyncMock, return_value={"conteudo_pagina": "texto"}):
        with patch("src.agents.web.extract_recipe_from_text", new_callable=AsyncMock, return_value=[mock_recipe]) as mock_fn:
            await agent.extract(url)

    _, kwargs = mock_fn.call_args
    assert kwargs["source_url"] == url
    assert kwargs["source_type"] == "web"


@pytest.mark.asyncio
async def test_web_agent_formats_sources_for_llm(mock_recipe):
    agent = WebAgent()
    url = "https://example.com/receita"
    sources = {
        "conteudo_pagina": "Bolo de chocolate...",
        "json_ld_recipe": '{"@type": "Recipe", "name": "Bolo"}',
    }

    with patch.object(agent.scraper, "scrape_sources", new_callable=AsyncMock, return_value=sources):
        with patch("src.agents.web.extract_recipe_from_text", new_callable=AsyncMock, return_value=[mock_recipe]) as mock_fn:
            await agent.extract(url)

    text = mock_fn.call_args[1]["text"]
    assert "## Conteudo Pagina" in text
    assert "## Json Ld Recipe" in text
