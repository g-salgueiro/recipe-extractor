# Multi-Source Merging Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fazer os extractors coletarem todas as fontes disponíveis (não apenas a primeira) e enviá-las ao LLM como seções rotuladas para extração mais completa de receitas, dicas e técnicas.

**Architecture:** Cada extractor retorna `dict[str, str]` com fontes nomeadas. Agents formatam seções rotuladas via helper compartilhado. Prompt do LLM melhorado para cruzar fontes e capturar técnicas culinárias. Web ganha extração de JSON-LD/schema.org.

**Tech Stack:** Python, Pydantic AI, yt-dlp, youtube-transcript-api, instaloader, BeautifulSoup, httpx, Playwright

---

### Task 1: Helper `format_sources` em BaseAgent

**Files:**
- Modify: `src/agents/base.py`
- Create: `tests/test_format_sources.py`

**Step 1: Write the failing test**

```python
# tests/test_format_sources.py
from src.agents.base import format_sources


def test_format_sources_single_source():
    result = format_sources({"legenda": "Texto da legenda"})
    assert "## Legenda" in result
    assert "Texto da legenda" in result


def test_format_sources_multiple_sources():
    sources = {
        "titulo": "Bolo de Chocolate",
        "descricao": "Ingredientes: farinha, açúcar",
        "legenda": "Hoje vou ensinar a fazer bolo",
    }
    result = format_sources(sources)
    assert "## Titulo" in result
    assert "## Descricao" in result
    assert "## Legenda" in result
    assert result.index("## Titulo") < result.index("## Descricao") < result.index("## Legenda")


def test_format_sources_empty_dict():
    result = format_sources({})
    assert result == ""


def test_format_sources_replaces_underscores():
    result = format_sources({"transcricao_whisper": "Texto"})
    assert "## Transcricao Whisper" in result
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_format_sources.py -v`
Expected: FAIL with ImportError — `format_sources` doesn't exist yet

**Step 3: Write minimal implementation**

Add to `src/agents/base.py`:

```python
def format_sources(sources: dict[str, str]) -> str:
    """Formata fontes nomeadas como seções rotuladas para o LLM."""
    if not sources:
        return ""
    sections = []
    for label, content in sources.items():
        readable = label.replace("_", " ").title()
        sections.append(f"## {readable}\n{content}")
    return "\n\n".join(sections)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_format_sources.py -v`
Expected: 4 PASS

**Step 5: Commit**

```bash
git add src/agents/base.py tests/test_format_sources.py
git commit -m "feat: add format_sources helper to BaseAgent module"
```

---

### Task 2: YouTubeExtractor — `extract_sources()` retornando dict

**Files:**
- Modify: `src/extractors/youtube_transcript.py`
- Modify: `tests/test_youtube_extractor.py`

**Step 1: Write the failing tests**

Adicionar ao `tests/test_youtube_extractor.py`:

```python
@pytest.mark.asyncio
async def test_extract_sources_returns_transcript_and_metadata():
    """Quando legenda e metadata estão disponíveis, retorna ambos."""
    extractor = YouTubeExtractor()

    snippet1 = MagicMock()
    snippet1.text = "Hoje vou fazer um bolo"
    snippet2 = MagicMock()
    snippet2.text = "com 2 xícaras de farinha"

    with patch(
        "src.extractors.youtube_transcript.YouTubeTranscriptApi.fetch",
        return_value=[snippet1, snippet2],
    ):
        with patch.object(
            extractor,
            "_get_metadata",
            return_value=("Bolo de Chocolate", "Ingredientes: 2 xícaras de farinha, 1 de açúcar, modo de preparo detalhado aqui com mais de cem caracteres para passar do threshold."),
        ):
            sources = await extractor.extract_sources("https://www.youtube.com/watch?v=abc123")

    assert "legenda" in sources
    assert "descricao" in sources
    assert "titulo" in sources
    assert "bolo" in sources["legenda"]
    assert "farinha" in sources["descricao"]


@pytest.mark.asyncio
async def test_extract_sources_skips_short_description():
    """Descrição curta (< 100 chars) não é incluída."""
    extractor = YouTubeExtractor()

    snippet = MagicMock()
    snippet.text = "Receita"

    with patch(
        "src.extractors.youtube_transcript.YouTubeTranscriptApi.fetch",
        return_value=[snippet],
    ):
        with patch.object(
            extractor, "_get_metadata", return_value=("Titulo", "Curta")
        ):
            sources = await extractor.extract_sources("https://www.youtube.com/watch?v=abc123")

    assert "legenda" in sources
    assert "descricao" not in sources
    assert "titulo" in sources


@pytest.mark.asyncio
async def test_extract_sources_uses_whisper_when_no_transcript_no_description():
    """Whisper só é usado quando não há legenda nem descrição."""
    from youtube_transcript_api import TranscriptsDisabled

    extractor = YouTubeExtractor()

    with patch(
        "src.extractors.youtube_transcript.YouTubeTranscriptApi.fetch",
        side_effect=TranscriptsDisabled("abc123"),
    ):
        with patch.object(extractor, "_get_metadata", return_value=("Titulo", "")):
            with patch.object(
                extractor,
                "_whisper_transcribe",
                new_callable=AsyncMock,
                return_value="Transcrição Whisper",
            ):
                sources = await extractor.extract_sources("https://www.youtube.com/watch?v=abc123")

    assert "transcricao_whisper" in sources
    assert sources["transcricao_whisper"] == "Transcrição Whisper"


@pytest.mark.asyncio
async def test_extract_sources_no_whisper_when_transcript_exists():
    """Whisper NÃO é acionado quando a legenda está disponível."""
    extractor = YouTubeExtractor()

    snippet = MagicMock()
    snippet.text = "Receita de bolo"

    with patch(
        "src.extractors.youtube_transcript.YouTubeTranscriptApi.fetch",
        return_value=[snippet],
    ):
        with patch.object(extractor, "_get_metadata", return_value=("Titulo", "")):
            with patch.object(
                extractor,
                "_whisper_transcribe",
                new_callable=AsyncMock,
            ) as mock_whisper:
                await extractor.extract_sources("https://www.youtube.com/watch?v=abc123")

    mock_whisper.assert_not_called()
```

**Step 2: Run test to verify they fail**

Run: `pytest tests/test_youtube_extractor.py -v -k "extract_sources"`
Expected: FAIL — `extract_sources` and `_get_metadata` don't exist

**Step 3: Write implementation**

Modify `src/extractors/youtube_transcript.py`:

1. Add `_get_metadata(url) -> tuple[str, str]` — returns (title, description) via yt-dlp
2. Add `extract_sources(url) -> dict[str, str]` — collects all available sources
3. Keep `extract_text(url)` as wrapper that delegates to `extract_sources()` and joins

```python
def _get_metadata(self, url: str) -> tuple[str, str]:
    """Obtém título e descrição do vídeo via yt-dlp sem download."""
    import yt_dlp

    opts = {"quiet": True, "no_warnings": True, "skip_download": True}
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return info.get("title", ""), info.get("description", "")

async def extract_sources(self, url: str) -> dict[str, str]:
    """Coleta todas as fontes disponíveis para o vídeo."""
    video_id = extract_video_id(url)
    sources: dict[str, str] = {}

    # Metadata (título + descrição) via yt-dlp
    try:
        title, description = await asyncio.to_thread(self._get_metadata, url)
        if title:
            sources["titulo"] = title
        if description and len(description.strip()) > 100:
            sources["descricao"] = description
    except Exception as e:
        logger.warning(f"YouTube metadata falhou: {e}")

    # Legenda via Transcript API
    try:
        api = YouTubeTranscriptApi()
        transcript = await asyncio.to_thread(
            api.fetch, video_id, languages=["pt", "en"]
        )
        sources["legenda"] = " ".join(snippet.text for snippet in transcript)
        logger.info("YouTube: legenda extraída via API")
    except Exception as e:
        logger.warning(f"YouTube transcript API falhou: {e}")

    # Whisper: último recurso, só se não tem legenda NEM descrição
    if "legenda" not in sources and "descricao" not in sources:
        logger.info("YouTube: fallback para Whisper")
        sources["transcricao_whisper"] = await self._whisper_transcribe(url)

    return sources

async def extract_text(self, url: str) -> str:
    """Wrapper legado: coleta fontes e retorna como texto único."""
    sources = await self.extract_sources(url)
    return "\n\n".join(sources.values())
```

Note: `_get_description` method is replaced by `_get_metadata`. Remove `_get_description`.

**Step 4: Run all YouTube extractor tests**

Run: `pytest tests/test_youtube_extractor.py -v`
Expected: ALL PASS (including old tests that use `extract_text`)

**Step 5: Update old tests that mock `_get_description`**

The old test `test_extract_text_falls_back_to_description` mocks `_get_description`. Update it to mock `_get_metadata` instead, returning `("Titulo", "descrição longa...")`.

The old test `test_extract_text_falls_back_to_whisper` mocks `_get_description` returning `""`. Update to mock `_get_metadata` returning `("", "")`.

**Step 6: Run all tests again**

Run: `pytest tests/test_youtube_extractor.py -v`
Expected: ALL PASS

**Step 7: Commit**

```bash
git add src/extractors/youtube_transcript.py tests/test_youtube_extractor.py
git commit -m "feat: YouTubeExtractor.extract_sources() collects all available sources"
```

---

### Task 3: YouTubeAgent — usar `extract_sources` + `format_sources`

**Files:**
- Modify: `src/agents/youtube.py`
- Modify: `tests/test_youtube_agent.py`

**Step 1: Write the failing test**

Add to `tests/test_youtube_agent.py`:

```python
@pytest.mark.asyncio
async def test_youtube_agent_sends_formatted_sources_to_llm(mock_recipe):
    agent = YouTubeAgent()
    url = "https://youtube.com/watch?v=abc"
    sources = {
        "titulo": "Bolo de Chocolate",
        "legenda": "Hoje vou ensinar a fazer bolo",
        "descricao": "Ingredientes: farinha, açúcar, etc.",
    }

    with patch.object(agent.extractor, "extract_sources", new_callable=AsyncMock, return_value=sources):
        with patch("src.agents.youtube.extract_recipe_from_text", new_callable=AsyncMock, return_value=[mock_recipe]) as mock_fn:
            await agent.extract(url)

    call_kwargs = mock_fn.call_args[1]
    text = call_kwargs["text"]
    assert "## Titulo" in text
    assert "## Legenda" in text
    assert "## Descricao" in text
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_youtube_agent.py::test_youtube_agent_sends_formatted_sources_to_llm -v`
Expected: FAIL — agent still uses `extract_text`

**Step 3: Update YouTubeAgent**

```python
from src.agents.base import BaseAgent, format_sources
from src.extractors.youtube_transcript import YouTubeExtractor
from src.llm import extract_recipe_from_text
from src.models.recipe import RecipeModel


class YouTubeAgent(BaseAgent):
    def __init__(self):
        self.extractor = YouTubeExtractor()

    async def extract(self, url: str) -> list[RecipeModel]:
        sources = await self.extractor.extract_sources(url)
        text = format_sources(sources)
        return await extract_recipe_from_text(
            text=text,
            source_url=url,
            source_type="youtube",
        )
```

**Step 4: Update existing agent tests**

Old tests mock `extract_text` — update them to mock `extract_sources` returning a dict instead. The assertions on `source_type` and `source_url` remain the same.

**Step 5: Run all agent tests**

Run: `pytest tests/test_youtube_agent.py -v`
Expected: ALL PASS

**Step 6: Commit**

```bash
git add src/agents/youtube.py tests/test_youtube_agent.py
git commit -m "feat: YouTubeAgent uses extract_sources + format_sources"
```

---

### Task 4: InstagramExtractor — retornar `sources` dict

**Files:**
- Modify: `src/extractors/instagram_loader.py`
- Modify: `tests/test_instagram_extractor.py`

**Step 1: Write the failing tests**

Add to `tests/test_instagram_extractor.py`:

```python
def test_extract_returns_sources_dict_with_caption():
    extractor = InstagramExtractor()
    mock_post = MagicMock()
    mock_post.caption = "Bolo de chocolate incrível! Ingredientes: 2 xícaras de farinha, modo de preparo abaixo..."
    mock_post.is_video = False

    with patch("src.extractors.instagram_loader.instaloader.Post.from_shortcode", return_value=mock_post):
        with patch("src.extractors.instagram_loader._fetch_og_description", return_value=""):
            result = extractor.extract("https://www.instagram.com/p/ABC123/")

    assert "sources" in result
    assert "caption" in result["sources"]
    assert result["images"] == []


def test_extract_includes_og_description_as_additional_source():
    extractor = InstagramExtractor()
    mock_post = MagicMock()
    mock_post.caption = "Bolo de chocolate incrível! Ingredientes: 2 xícaras de farinha e modo de preparo."
    mock_post.is_video = False

    with patch("src.extractors.instagram_loader.instaloader.Post.from_shortcode", return_value=mock_post):
        with patch("src.extractors.instagram_loader._fetch_og_description", return_value="OG: Receita completa de bolo"):
            result = extractor.extract("https://www.instagram.com/p/ABC123/")

    assert "caption" in result["sources"]
    assert "og_description" in result["sources"]


def test_extract_video_includes_transcription_source():
    extractor = InstagramExtractor()
    mock_post = MagicMock()
    mock_post.caption = "Steak Au Poivre recipe!"
    mock_post.is_video = True

    with patch("src.extractors.instagram_loader.instaloader.Post.from_shortcode", return_value=mock_post):
        with patch.object(extractor, "_transcribe_video", return_value="Add butter and cream..."):
            with patch("src.extractors.instagram_loader._fetch_og_description", return_value=""):
                result = extractor.extract("https://www.instagram.com/p/ABC123/")

    assert "caption" in result["sources"]
    assert "transcricao_audio" in result["sources"]
```

**Step 2: Run to verify they fail**

Run: `pytest tests/test_instagram_extractor.py -v -k "sources_dict or og_description_as_additional or transcription_source"`
Expected: FAIL — result has `text` key, not `sources`

**Step 3: Update InstagramExtractor**

Change `extract()` to return `{"sources": dict[str, str], "images": list[bytes]}`:

```python
def extract(self, url: str) -> dict:
    """Retorna {'sources': dict[str, str], 'images': list[bytes]}."""
    sources: dict[str, str] = {}
    images: list[bytes] = []

    # Sempre tentar og:description como fonte adicional
    og_desc = _fetch_og_description(url)
    if og_desc:
        sources["og_description"] = og_desc

    try:
        insta_result = self._extract_via_instaloader(url)
        sources.update(insta_result["sources"])
        images = insta_result["images"]
    except Exception as e:
        logger.warning(f"instaloader falhou ({e}), tentando fallbacks")
        # Se instaloader falhou e é vídeo, tenta yt-dlp + Whisper
        try:
            transcription = self._transcribe_video(url)
            sources["transcricao_audio"] = transcription
        except Exception as e2:
            logger.warning(f"yt-dlp + Whisper falhou: {e2}")

    return {"sources": sources, "images": images}

def _extract_via_instaloader(self, url: str) -> dict:
    shortcode = extract_shortcode(url)
    post = instaloader.Post.from_shortcode(self._loader.context, shortcode)
    caption = post.caption or ""
    sources: dict[str, str] = {}
    images: list[bytes] = []

    if caption:
        sources["caption"] = caption

    if post.is_video:
        logger.info("Instagram: post de vídeo, transcrevendo")
        transcription = self._transcribe_video(url)
        sources["transcricao_audio"] = transcription
    elif len(caption.strip()) < _CAPTION_MIN_LENGTH:
        logger.info("Instagram: caption curta, baixando imagens")
        images = self._download_images(post)

    return {"sources": sources, "images": images}
```

**Step 4: Update old Instagram extractor tests**

Update all existing tests to check `result["sources"]["caption"]` instead of `result["text"]`. The key change is:
- `result["text"]` → `result["sources"]["caption"]` or similar
- The video test checks `result["sources"]["transcricao_audio"]` instead of `"Add butter" in result["text"]`

**Step 5: Run all Instagram extractor tests**

Run: `pytest tests/test_instagram_extractor.py -v`
Expected: ALL PASS

**Step 6: Commit**

```bash
git add src/extractors/instagram_loader.py tests/test_instagram_extractor.py
git commit -m "feat: InstagramExtractor returns sources dict instead of text string"
```

---

### Task 5: InstagramAgent — usar `sources` dict + `format_sources`

**Files:**
- Modify: `src/agents/instagram.py`
- Modify: `tests/test_instagram_agent.py`

**Step 1: Write the failing test**

```python
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
```

**Step 2: Run to verify it fails**

Run: `pytest tests/test_instagram_agent.py::test_instagram_agent_formats_sources_for_llm -v`
Expected: FAIL

**Step 3: Update InstagramAgent**

```python
import asyncio

from src.agents.base import BaseAgent, format_sources
from src.extractors.instagram_loader import InstagramExtractor
from src.llm import extract_recipe_from_images, extract_recipe_from_text
from src.models.recipe import RecipeModel


class InstagramAgent(BaseAgent):
    def __init__(self):
        self.extractor = InstagramExtractor()

    async def extract(self, url: str) -> list[RecipeModel]:
        extracted = await asyncio.to_thread(self.extractor.extract, url)
        sources = extracted["sources"]
        images = extracted["images"]

        if images:
            caption = format_sources(sources)
            return await extract_recipe_from_images(
                images=images,
                caption=caption,
                source_url=url,
                source_type="instagram",
            )

        text = format_sources(sources)
        return await extract_recipe_from_text(
            text=text,
            source_url=url,
            source_type="instagram",
        )
```

**Step 4: Update existing Instagram agent tests**

Change `extracted` dicts from `{"text": ..., "images": ...}` to `{"sources": {"caption": ...}, "images": ...}`.

**Step 5: Run all tests**

Run: `pytest tests/test_instagram_agent.py -v`
Expected: ALL PASS

**Step 6: Commit**

```bash
git add src/agents/instagram.py tests/test_instagram_agent.py
git commit -m "feat: InstagramAgent uses sources dict + format_sources"
```

---

### Task 6: WebScraper — `scrape_sources()` com JSON-LD

**Files:**
- Modify: `src/extractors/web_scraper.py`
- Modify: `tests/test_web_scraper.py`

**Step 1: Write the failing tests**

Add to `tests/test_web_scraper.py`:

```python
import json
from src.extractors.web_scraper import _extract_json_ld_recipe

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
<body><main><p>Receita de bolo</p></main></body>
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
async def test_scrape_sources_returns_dict():
    scraper = WebScraper()
    mock_response = MagicMock()
    mock_response.text = SAMPLE_HTML_WITH_JSONLD
    mock_response.raise_for_status = MagicMock()

    with patch("src.extractors.web_scraper.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=mock_response
        )
        sources = await scraper.scrape_sources("https://example.com/receita")

    assert "conteudo_pagina" in sources
    assert "json_ld_recipe" in sources


@pytest.mark.asyncio
async def test_scrape_sources_no_jsonld():
    scraper = WebScraper()
    mock_response = MagicMock()
    mock_response.text = SAMPLE_HTML
    mock_response.raise_for_status = MagicMock()

    with patch("src.extractors.web_scraper.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=mock_response
        )
        sources = await scraper.scrape_sources("https://example.com/receita")

    assert "conteudo_pagina" in sources
    assert "json_ld_recipe" not in sources
```

**Step 2: Run to verify they fail**

Run: `pytest tests/test_web_scraper.py -v -k "json_ld or scrape_sources"`
Expected: FAIL — functions don't exist

**Step 3: Implement `_extract_json_ld_recipe` and `scrape_sources`**

Add to `src/extractors/web_scraper.py`:

```python
import json

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
```

Add `scrape_sources` to `WebScraper`:

```python
async def scrape_sources(self, url: str) -> dict[str, str]:
    """Retorna dict de fontes: conteudo_pagina + json_ld_recipe (se disponível)."""
    sources: dict[str, str] = {}
    raw_html = await self._fetch_html(url)

    text = _html_to_text(raw_html)
    if text and len(text.strip()) >= _MIN_CONTENT_LENGTH:
        sources["conteudo_pagina"] = text
    else:
        # Fallback Playwright
        raw_html = await self._fetch_html_playwright(url)
        sources["conteudo_pagina"] = _html_to_text(raw_html)

    json_ld = _extract_json_ld_recipe(raw_html)
    if json_ld:
        sources["json_ld_recipe"] = json_ld

    return sources
```

Refactor: extract `_fetch_html(url) -> str` (httpx) and `_fetch_html_playwright(url) -> str` from existing methods, so both `scrape` (legacy) and `scrape_sources` can use them. Keep `scrape()` working as wrapper.

**Step 4: Run all web scraper tests**

Run: `pytest tests/test_web_scraper.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add src/extractors/web_scraper.py tests/test_web_scraper.py
git commit -m "feat: WebScraper.scrape_sources() with JSON-LD extraction"
```

---

### Task 7: WebAgent — usar `scrape_sources` + `format_sources`

**Files:**
- Modify: `src/agents/web.py`
- Modify: `tests/test_web_agent.py`

**Step 1: Write the failing test**

```python
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
```

**Step 2: Run to verify it fails**

Run: `pytest tests/test_web_agent.py::test_web_agent_formats_sources_for_llm -v`
Expected: FAIL

**Step 3: Update WebAgent**

```python
from src.agents.base import BaseAgent, format_sources
from src.extractors.web_scraper import WebScraper
from src.llm import extract_recipe_from_text
from src.models.recipe import RecipeModel


class WebAgent(BaseAgent):
    def __init__(self):
        self.scraper = WebScraper()

    async def extract(self, url: str) -> list[RecipeModel]:
        sources = await self.scraper.scrape_sources(url)
        text = format_sources(sources)
        return await extract_recipe_from_text(
            text=text,
            source_url=url,
            source_type="web",
        )
```

**Step 4: Update existing web agent tests**

Change mocks from `scrape` to `scrape_sources` returning dict.

**Step 5: Run all tests**

Run: `pytest tests/test_web_agent.py -v`
Expected: ALL PASS

**Step 6: Commit**

```bash
git add src/agents/web.py tests/test_web_agent.py
git commit -m "feat: WebAgent uses scrape_sources + format_sources"
```

---

### Task 8: Prompt do LLM — cruzamento de fontes + técnicas culinárias

**Files:**
- Modify: `src/llm.py`
- Modify: `tests/test_llm.py`

**Step 1: Write the failing test**

```python
def test_system_prompt_mentions_cross_referencing():
    from src.llm import _SYSTEM_PROMPT
    assert "cruze" in _SYSTEM_PROMPT.lower() or "múltiplas fontes" in _SYSTEM_PROMPT.lower()


def test_system_prompt_mentions_techniques():
    from src.llm import _SYSTEM_PROMPT
    assert "técnica" in _SYSTEM_PROMPT.lower() or "desossar" in _SYSTEM_PROMPT.lower()
```

**Step 2: Run to verify they fail**

Run: `pytest tests/test_llm.py -v -k "cross_referencing or techniques"`
Expected: FAIL

**Step 3: Update `_SYSTEM_PROMPT` and `_MAX_TEXT_LENGTH`**

```python
_SYSTEM_PROMPT = """Você é um especialista em extração de receitas culinárias.
Dado um texto (ou imagem), extraia TODAS as receitas presentes e retorne em formato estruturado.

Regras:
- O conteúdo pode vir de múltiplas fontes (legenda, descrição, transcrição). Cruze as informações para obter a receita mais completa possível — por exemplo, use quantidades exatas da descrição e instruções detalhadas da legenda.
- O conteúdo pode conter UMA ou MÚLTIPLAS receitas — extraia todas sem exceção
- Para cada receita, extraia TODOS os ingredientes com quantidades e unidades exatas
- Extraia as instruções passo a passo de cada receita
- Coloque dicas, variações e observações do chef em "tips" da receita correspondente. Dicas incluem técnicas de preparo de ingredientes (como desossar, limpar, cortar), substituições possíveis, e observações sobre tempo/temperatura.
- Se uma informação estiver ausente, use null
- Defina extraction_confidence entre 0.0 e 1.0 indicando a clareza de cada receita
- Se não encontrar nenhuma receita, retorne uma lista vazia em "recipes"
- Responda sempre em português"""

_MAX_TEXT_LENGTH = 24_000  # ~6k tokens
```

**Step 4: Update the truncation test**

The existing test `test_extract_recipe_from_text_truncates_long_input` checks for 12_500 limit. Update to check for 24_500 (~24k + prompt overhead).

**Step 5: Run all LLM tests**

Run: `pytest tests/test_llm.py -v`
Expected: ALL PASS

**Step 6: Commit**

```bash
git add src/llm.py tests/test_llm.py
git commit -m "feat: improve LLM prompt for cross-referencing sources and capturing techniques"
```

---

### Task 9: Run full test suite and verify

**Step 1: Run all tests**

Run: `pytest -v`
Expected: ALL PASS (count should be ~60+ with new tests)

**Step 2: Fix any failures**

If tests fail, identify root cause and fix.

**Step 3: Commit if any fixes were needed**

```bash
git add -A
git commit -m "fix: resolve test issues from multi-source merging"
```

---

### Task 10: Update MEMORY.md

**Files:**
- Modify: `/Users/gabrielsalgueiro/.claude/projects/-Users-gabrielsalgueiro-Documents-recipes/memory/MEMORY.md`

Update the architecture section to reflect the new multi-source approach:
- Extractors return `dict[str, str]` not `str`
- Agents use `format_sources()` to create labeled sections
- Instagram returns `{"sources": dict, "images": list}` not `{"text": str, "images": list}`
- WebScraper has `scrape_sources()` and `_extract_json_ld_recipe()`
- `_MAX_TEXT_LENGTH` is now 24_000
