# tests/test_main.py
import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from src.main import run, save_outputs
from src.models.recipe import Ingredient, RecipeModel


@pytest.fixture
def mock_recipe():
    return RecipeModel(
        title="Bolo de Chocolate",
        ingredients=[Ingredient(name="farinha", quantity="2", unit="xícaras")],
        steps=["Misture tudo", "Asse por 40min"],
        tips=["Use cacau 70%"],
        extraction_confidence=0.95,
        source_url="https://youtube.com/watch?v=abc",
        source_type="youtube",
        extracted_at=datetime(2026, 2, 26, tzinfo=timezone.utc),
    )


def test_save_outputs_creates_json_and_markdown(tmp_path, mock_recipe):
    save_outputs(mock_recipe, output_dir=tmp_path)

    json_files = list(tmp_path.glob("*.json"))
    md_files = list(tmp_path.glob("*.md"))

    assert len(json_files) == 1
    assert len(md_files) == 1

    data = json.loads(json_files[0].read_text())
    assert data["title"] == "Bolo de Chocolate"
    assert len(data["ingredients"]) == 1

    md_content = md_files[0].read_text()
    assert "# Bolo de Chocolate" in md_content
    assert "farinha" in md_content


@pytest.mark.asyncio
async def test_run_dispatches_to_youtube_agent(mock_recipe):
    url = "https://www.youtube.com/watch?v=abc123"
    with patch("src.main.YouTubeAgent") as MockAgent:
        instance = MockAgent.return_value
        instance.extract = AsyncMock(return_value=mock_recipe)
        result = await run(url)

    assert result.title == "Bolo de Chocolate"
    MockAgent.assert_called_once()


@pytest.mark.asyncio
async def test_run_dispatches_to_instagram_agent(mock_recipe):
    url = "https://www.instagram.com/p/ABC123/"
    with patch("src.main.InstagramAgent") as MockAgent:
        instance = MockAgent.return_value
        instance.extract = AsyncMock(return_value=mock_recipe)
        result = await run(url)

    MockAgent.assert_called_once()


@pytest.mark.asyncio
async def test_run_dispatches_to_web_agent(mock_recipe):
    url = "https://www.tudogostoso.com.br/receita/1"
    with patch("src.main.WebAgent") as MockAgent:
        instance = MockAgent.return_value
        instance.extract = AsyncMock(return_value=mock_recipe)
        result = await run(url)

    MockAgent.assert_called_once()


@pytest.mark.asyncio
async def test_run_raises_on_unsupported_url():
    from src.router import UnsupportedSourceError

    with pytest.raises(UnsupportedSourceError):
        await run("not-a-url")
