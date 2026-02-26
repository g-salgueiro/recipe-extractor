# src/extractors/web_scraper.py
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


class WebScraper:
    async def scrape(self, url: str) -> str:
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

    async def _scrape_httpx(self, url: str) -> str:
        async with httpx.AsyncClient(follow_redirects=True, headers=_HEADERS) as client:
            response = await client.get(url, timeout=30.0)
            response.raise_for_status()
        return _html_to_text(response.text)

    async def _scrape_playwright(self, url: str) -> str:
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            try:
                page = await browser.new_page()
                await page.goto(url, wait_until="networkidle", timeout=30_000)
                content = await page.content()
            finally:
                await browser.close()
        return _html_to_text(content)
