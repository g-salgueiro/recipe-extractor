# tests/test_web_scraper.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.extractors.web_scraper import WebScraper

SAMPLE_HTML = """
<html>
<head><title>Bolo de Chocolate</title></head>
<body>
<nav>Menu de navegação</nav>
<main>
  <h1>Bolo de Chocolate</h1>
  <p>Ingredientes: 2 xícaras de farinha de trigo, 1 xícara de açúcar, 1/2 xícara de cacau em pó,
  3 ovos, 1 xícara de leite, 1/2 xícara de óleo vegetal, 1 colher de sopa de fermento em pó.</p>
  <p>Modo de preparo: Misture todos os ingredientes secos em uma tigela grande. Adicione os ovos,
  o leite e o óleo. Misture bem até obter uma massa homogênea. Leve ao forno preaquecido a 180 graus
  por aproximadamente 40 minutos ou até que o palito saia limpo.</p>
</main>
<footer>Rodapé do site</footer>
</body>
</html>
"""


@pytest.mark.asyncio
async def test_scrape_extracts_main_content():
    scraper = WebScraper()
    mock_response = MagicMock()
    mock_response.text = SAMPLE_HTML
    mock_response.raise_for_status = MagicMock()

    with patch("src.extractors.web_scraper.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=mock_response
        )
        text = await scraper.scrape("https://example.com/receita")

    assert "Bolo de Chocolate" in text
    assert "farinha" in text
    assert "Menu de navegação" not in text
    assert "Rodapé do site" not in text


@pytest.mark.asyncio
async def test_scrape_falls_back_to_playwright_on_httpx_error():
    scraper = WebScraper()

    with patch.object(scraper, "_scrape_httpx", side_effect=Exception("Connection refused")):
        with patch.object(
            scraper, "_scrape_playwright", new_callable=AsyncMock, return_value="Conteúdo via Playwright"
        ):
            text = await scraper.scrape("https://example.com/receita")

    assert text == "Conteúdo via Playwright"


@pytest.mark.asyncio
async def test_scrape_falls_back_to_playwright_when_content_too_short():
    scraper = WebScraper()

    with patch.object(scraper, "_scrape_httpx", new_callable=AsyncMock, return_value="curto"):
        with patch.object(
            scraper,
            "_scrape_playwright",
            new_callable=AsyncMock,
            return_value="Conteúdo completo da receita com ingredientes e modo de preparo detalhado",
        ):
            text = await scraper.scrape("https://example.com/receita")

    assert "ingredientes" in text
