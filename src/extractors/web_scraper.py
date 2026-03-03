# src/extractors/web_scraper.py
"""
Scraper de páginas web com dois modos de operação:

1. **httpx** — requisição HTTP direta. Funciona para a maioria dos sites de receitas
   que servem HTML estático. Rápido e sem dependências pesadas.

2. **Playwright** — fallback para sites com renderização JavaScript (SPAs). Usado
   quando httpx retorna conteúdo vazio ou muito curto (< 200 chars).

O HTML é limpo por `_html_to_text`: remove scripts, estilos, nav, footer e header,
depois extrai o nó mais relevante (main > article > #content > .recipe > body).
"""
import json
import logging

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

_MIN_CONTENT_LENGTH = 200
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


def _html_to_text(html: str) -> str:
    """Extrai o texto principal do HTML, removendo elementos de navegação e boilerplate."""
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()
    main = (
        soup.find("main")
        or soup.find("article")
        or soup.find(id="content")
        or soup.find(class_="recipe")
        or soup.body
    )
    return main.get_text(separator="\n", strip=True) if main else ""


def _extract_json_ld_recipe(html: str) -> str | None:
    """Extrai dados Recipe de JSON-LD/schema.org se disponível."""
    soup = BeautifulSoup(html, "lxml")
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string)
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(data, dict) and data.get("@type") == "Recipe":
            return json.dumps(data, ensure_ascii=False, indent=2)
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and item.get("@type") == "Recipe":
                    return json.dumps(item, ensure_ascii=False, indent=2)
    return None


class WebScraper:
    async def scrape(self, url: str) -> str:
        """Retorna o texto da página, usando Playwright como fallback se necessário."""
        try:
            text = await self._scrape_httpx(url)
            if text and len(text.strip()) >= _MIN_CONTENT_LENGTH:
                logger.info("Web: extraído via httpx")
                return text
            logger.warning("Web: conteúdo muito curto via httpx, tentando Playwright")
        except Exception as e:
            logger.warning(f"Web: httpx falhou: {e}")

        logger.info("Web: fallback para Playwright")
        return await self._scrape_playwright(url)

    async def scrape_sources(self, url: str) -> dict[str, str]:
        """Retorna dict de fontes: conteudo_pagina + json_ld_recipe (se disponível)."""
        sources: dict[str, str] = {}

        try:
            raw_html = await self._fetch_html(url)
            text = _html_to_text(raw_html)
            if not text or len(text.strip()) < _MIN_CONTENT_LENGTH:
                logger.warning("Web: conteúdo muito curto via httpx, tentando Playwright")
                raw_html = await self._fetch_html_playwright(url)
                text = _html_to_text(raw_html)
        except Exception as e:
            logger.warning(f"Web: httpx falhou: {e}")
            raw_html = await self._fetch_html_playwright(url)
            text = _html_to_text(raw_html)

        if text:
            sources["conteudo_pagina"] = text

        json_ld = _extract_json_ld_recipe(raw_html)
        if json_ld:
            sources["json_ld_recipe"] = json_ld

        return sources

    async def _fetch_html(self, url: str) -> str:
        """Fetch raw HTML via httpx."""
        async with httpx.AsyncClient(follow_redirects=True, headers=_HEADERS) as client:
            response = await client.get(url, timeout=30.0)
            response.raise_for_status()
        return response.text

    async def _fetch_html_playwright(self, url: str) -> str:
        """Fetch raw HTML via Playwright."""
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            try:
                page = await browser.new_page()
                await page.goto(url, wait_until="networkidle", timeout=30_000)
                content = await page.content()
            finally:
                await browser.close()
        return content

    async def _scrape_httpx(self, url: str) -> str:
        raw_html = await self._fetch_html(url)
        return _html_to_text(raw_html)

    async def _scrape_playwright(self, url: str) -> str:
        """Renderiza a página com Chromium headless e extrai o texto resultante."""
        raw_html = await self._fetch_html_playwright(url)
        return _html_to_text(raw_html)
