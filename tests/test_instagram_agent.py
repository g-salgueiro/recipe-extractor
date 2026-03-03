# tests/test_instagram_agent.py
"""Testes unitários do InstagramAgent.

Verifica as duas rotas LLM:
- caption presente (texto longo) → `extract_recipe_from_text`
- imagens presentes (caption curta / foto) → `extract_recipe_from_images`

O `InstagramExtractor.extract` é mockado para retornar dicts controlados,
isolando o agente de chamadas reais ao Instagram ou ao LLM.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from src.agents.instagram import InstagramAgent
from src.agents.base import format_sources
from src.models.recipe import Ingredient, RecipeModel


@pytest.fixture
def mock_recipe():
    return RecipeModel(
        title="Bolo",
        ingredients=[Ingredient(name="farinha", quantity="2", unit="xícaras")],
        steps=["Passo 1"],
        extraction_confidence=0.9,
        source_url="https://instagram.com/p/ABC/",
        source_type="instagram",
    )


@pytest.mark.asyncio
async def test_instagram_agent_uses_text_when_caption_present(mock_recipe):
    agent = InstagramAgent()
    url = "https://www.instagram.com/p/ABC123/"
    extracted = {
        "sources": {"caption": "Bolo delicioso! Ingredientes: 2 xícaras de farinha, açúcar e ovos..."},
        "images": [],
    }

    with patch.object(agent.extractor, "extract", return_value=extracted):
        with patch("src.agents.instagram.extract_recipe_from_text", new_callable=AsyncMock, return_value=[mock_recipe]) as mock_fn:
            result = await agent.extract(url)

    mock_fn.assert_called_once()
    assert mock_fn.call_args[1]["source_type"] == "instagram"
    assert result[0].source_type == "instagram"


@pytest.mark.asyncio
async def test_instagram_agent_uses_vision_when_images_present(mock_recipe):
    agent = InstagramAgent()
    url = "https://www.instagram.com/p/ABC123/"
    extracted = {"sources": {"caption": "Yummy!"}, "images": [b"fake_image_bytes"]}

    with patch.object(agent.extractor, "extract", return_value=extracted):
        with patch("src.agents.instagram.extract_recipe_from_images", new_callable=AsyncMock, return_value=[mock_recipe]) as mock_fn:
            result = await agent.extract(url)

    expected_caption = format_sources({"caption": "Yummy!"})
    mock_fn.assert_called_once_with(
        images=[b"fake_image_bytes"],
        caption=expected_caption,
        source_url=url,
        source_type="instagram",
    )
    assert result[0].source_type == "instagram"


@pytest.mark.asyncio
async def test_instagram_agent_formats_sources_for_llm(mock_recipe):
    agent = InstagramAgent()
    url = "https://www.instagram.com/p/ABC123/"
    extracted = {
        "sources": {"caption": "Receita de bolo!", "og_description": "Bolo completo"},
        "images": [],
    }

    with patch.object(agent.extractor, "extract", return_value=extracted):
        with patch("src.agents.instagram.extract_recipe_from_text", new_callable=AsyncMock, return_value=[mock_recipe]) as mock_fn:
            await agent.extract(url)

    text = mock_fn.call_args[1]["text"]
    assert "## Caption" in text
    assert "## Og Description" in text
