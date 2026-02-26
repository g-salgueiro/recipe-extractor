# tests/test_llm.py
"""Testes unitários da camada LLM.

Testa `extract_recipe_from_text` e `extract_recipe_from_images` mockando
`_get_agent()` para evitar chamadas reais à API. Verifica:
- Retorno de lista de `RecipeModel` com metadados corretos
- Suporte a múltiplas receitas por extração (via `RecipeCollection`)
- Truncamento de textos longos no limite de tokens
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.llm import create_recipe_agent, extract_recipe_from_images, extract_recipe_from_text
from src.models.recipe import Ingredient, RecipeCollection, RecipeContent, RecipeModel


@pytest.fixture
def mock_recipe_content():
    return RecipeContent(
        title="Bolo de Chocolate",
        ingredients=[Ingredient(name="farinha", quantity="2", unit="xícaras")],
        steps=["Passo 1"],
        extraction_confidence=0.9,
    )


@pytest.fixture
def mock_collection(mock_recipe_content):
    return RecipeCollection(recipes=[mock_recipe_content])


def test_create_recipe_agent_returns_agent():
    from pydantic_ai import Agent
    agent = create_recipe_agent()
    assert isinstance(agent, Agent)


@pytest.mark.asyncio
async def test_extract_recipe_from_text_returns_list(mock_collection):
    mock_agent = MagicMock()
    mock_result = MagicMock()
    mock_result.output = mock_collection
    mock_agent.run = AsyncMock(return_value=mock_result)

    with patch("src.llm._get_agent", return_value=mock_agent):
        recipes = await extract_recipe_from_text(
            text="Bolo de Chocolate com 2 xícaras de farinha...",
            source_url="https://example.com",
            source_type="web",
        )

    assert isinstance(recipes, list)
    assert len(recipes) == 1
    assert isinstance(recipes[0], RecipeModel)
    assert recipes[0].title == "Bolo de Chocolate"
    assert recipes[0].source_url == "https://example.com"
    assert recipes[0].source_type == "web"


@pytest.mark.asyncio
async def test_extract_recipe_from_text_returns_multiple_recipes():
    contents = [
        RecipeContent(title="Receita A", ingredients=[], steps=[], extraction_confidence=0.9),
        RecipeContent(title="Receita B", ingredients=[], steps=[], extraction_confidence=0.8),
    ]
    collection = RecipeCollection(recipes=contents)
    mock_agent = MagicMock()
    mock_result = MagicMock()
    mock_result.output = collection
    mock_agent.run = AsyncMock(return_value=mock_result)

    with patch("src.llm._get_agent", return_value=mock_agent):
        recipes = await extract_recipe_from_text("texto", "https://example.com", "web")

    assert len(recipes) == 2
    assert recipes[0].title == "Receita A"
    assert recipes[1].title == "Receita B"


@pytest.mark.asyncio
async def test_extract_recipe_from_text_truncates_long_input(mock_collection):
    long_text = "a" * 20_000
    mock_agent = MagicMock()
    mock_result = MagicMock()
    mock_result.output = mock_collection
    mock_agent.run = AsyncMock(return_value=mock_result)

    with patch("src.llm._get_agent", return_value=mock_agent):
        await extract_recipe_from_text(long_text, "https://example.com", "web")

    call_args = mock_agent.run.call_args[0][0]
    assert len(call_args) <= 12_500  # prompt + 12_000 chars max


@pytest.mark.asyncio
async def test_extract_recipe_from_images_returns_list(mock_collection):
    mock_agent = MagicMock()
    mock_result = MagicMock()
    mock_result.output = mock_collection
    mock_agent.run = AsyncMock(return_value=mock_result)

    with patch("src.llm._get_agent", return_value=mock_agent):
        recipes = await extract_recipe_from_images(
            images=[b"fake_jpeg"],
            caption="",
            source_url="https://instagram.com/p/ABC/",
            source_type="instagram",
        )

    assert isinstance(recipes, list)
    assert len(recipes) == 1
    assert recipes[0].source_type == "instagram"
