# tests/test_web_scraper.py
"""Testes unitários do WebScraper.

Verifica o caminho httpx (sucesso), o fallback para Playwright quando httpx
falha com exceção, e o fallback quando o conteúdo retornado é muito curto.
Playwright é mockado para evitar a inicialização de um browser real.
"""
import json

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.extractors.web_scraper import WebScraper, _extract_json_ld_recipe

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


# --- JSON-LD and scrape_sources tests ---

SAMPLE_HTML_WITH_JSONLD = """
<html>
<head>
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Recipe",
  "name": "Bolo de Chocolate",
  "recipeIngredient": ["2 xícaras de farinha", "1 xícara de açúcar"],
  "recipeInstructions": [{"text": "Misture tudo"}, {"text": "Asse por 40 min"}]
}
</script>
</head>
<body><main><p>Receita de bolo com ingredientes e modo de preparo detalhado para que o texto tenha mais de duzentos caracteres e passe do threshold de conteúdo mínimo exigido pelo scraper. Misture farinha, açúcar e cacau. Asse por quarenta minutos.</p></main></body>
</html>
"""


def test_extract_json_ld_recipe_found():
    result = _extract_json_ld_recipe(SAMPLE_HTML_WITH_JSONLD)
    assert result is not None
    data = json.loads(result)
    assert data["@type"] == "Recipe"
    assert data["name"] == "Bolo de Chocolate"


def test_extract_json_ld_recipe_not_found():
    result = _extract_json_ld_recipe(SAMPLE_HTML)
    assert result is None


@pytest.mark.asyncio
async def test_scrape_sources_returns_dict_with_jsonld():
    scraper = WebScraper()

    with patch.object(
        scraper, "_fetch_html", new_callable=AsyncMock, return_value=SAMPLE_HTML_WITH_JSONLD
    ):
        sources = await scraper.scrape_sources("https://example.com/receita")

    assert "conteudo_pagina" in sources
    assert "json_ld_recipe" in sources


@pytest.mark.asyncio
async def test_scrape_sources_no_jsonld():
    scraper = WebScraper()

    with patch.object(
        scraper, "_fetch_html", new_callable=AsyncMock, return_value=SAMPLE_HTML
    ):
        sources = await scraper.scrape_sources("https://example.com/receita")

    assert "conteudo_pagina" in sources
    assert "json_ld_recipe" not in sources
