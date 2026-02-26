# tests/test_llm.py
from unittest.mock import MagicMock, patch

import pytest

from src.llm import create_recipe_agent, extract_recipe_from_images, extract_recipe_from_text
from src.models.recipe import Ingredient, RecipeContent, RecipeModel


@pytest.fixture
def mock_recipe_content():
    return RecipeContent(
        title="Bolo de Chocolate",
        ingredients=[Ingredient(name="farinha", quantity="2", unit="xícaras")],
        steps=["Passo 1"],
        extraction_confidence=0.9,
    )


def test_create_recipe_agent_returns_agent():
    from pydantic_ai import Agent
    agent = create_recipe_agent()
    assert isinstance(agent, Agent)


def test_extract_recipe_from_text_returns_recipe_model(mock_recipe_content):
    with patch("src.llm._agent") as mock_agent:
        mock_result = MagicMock()
        mock_result.data = mock_recipe_content
        mock_agent.run_sync.return_value = mock_result

        recipe = extract_recipe_from_text(
            text="Bolo de Chocolate com 2 xícaras de farinha...",
            source_url="https://example.com",
            source_type="web",
        )

    assert isinstance(recipe, RecipeModel)
    assert recipe.title == "Bolo de Chocolate"
    assert recipe.source_url == "https://example.com"
    assert recipe.source_type == "web"


def test_extract_recipe_from_text_truncates_long_input(mock_recipe_content):
    long_text = "a" * 20_000
    with patch("src.llm._agent") as mock_agent:
        mock_result = MagicMock()
        mock_result.data = mock_recipe_content
        mock_agent.run_sync.return_value = mock_result

        extract_recipe_from_text(long_text, "https://example.com", "web")

        call_args = mock_agent.run_sync.call_args[0][0]
        assert len(call_args) <= 12_500  # prompt + 12_000 chars max


def test_extract_recipe_from_images_returns_recipe_model(mock_recipe_content):
    with patch("src.llm._agent") as mock_agent:
        mock_result = MagicMock()
        mock_result.data = mock_recipe_content
        mock_agent.run_sync.return_value = mock_result

        recipe = extract_recipe_from_images(
            images=[b"fake_jpeg"],
            caption="",
            source_url="https://instagram.com/p/ABC/",
            source_type="instagram",
        )

    assert isinstance(recipe, RecipeModel)
    assert recipe.source_type == "instagram"
