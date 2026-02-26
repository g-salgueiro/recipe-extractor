# Recipe Extractor MVP — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a CLI tool that extracts structured culinary recipes from YouTube, Instagram, and web URLs using specialized AI agents per source.

**Architecture:** `SourceRouter` detects the URL type and dispatches to a specialized Agent (YouTube/Instagram/Web). Each Agent uses an Extractor to collect raw text or images, then passes to a Pydantic AI + OpenRouter LLM agent which returns a validated `RecipeModel`. Output is saved as JSON and Markdown.

**Tech Stack:** Python 3.12+, Pydantic AI, OpenRouter, youtube-transcript-api, yt-dlp, openai-whisper, instaloader, httpx, BeautifulSoup4, Playwright, pytest, pytest-asyncio

---

## Task 1: Project Setup

**Files:**
- Create: `pyproject.toml`
- Create: `src/__init__.py`
- Create: `src/agents/__init__.py`
- Create: `src/extractors/__init__.py`
- Create: `src/models/__init__.py`
- Create: `.env.example`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`

**Step 1: Create directory structure**

```bash
mkdir -p src/agents src/extractors src/models tests docs/plans
touch src/__init__.py src/agents/__init__.py src/extractors/__init__.py src/models/__init__.py
touch tests/__init__.py tests/conftest.py
```

**Step 2: Write `pyproject.toml`**

```toml
[project]
name = "recipe-extractor"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "pydantic-ai[openai]>=0.0.20",
    "youtube-transcript-api>=0.6.3",
    "yt-dlp>=2024.12.0",
    "openai-whisper>=20231117",
    "instaloader>=4.13.1",
    "httpx>=0.27.0",
    "beautifulsoup4>=4.12.3",
    "lxml>=5.2.0",
    "playwright>=1.44.0",
    "python-dotenv>=1.0.1",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.2.0",
    "pytest-asyncio>=0.23.7",
    "pytest-mock>=3.14.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.hatch.build.targets.wheel]
packages = ["src"]
```

**Step 3: Write `.env.example`**

```
OPENROUTER_API_KEY=your_key_here
OPENROUTER_MODEL=openai/gpt-4o
INSTAGRAM_USERNAME=
INSTAGRAM_PASSWORD=
WHISPER_MODEL_SIZE=base
```

**Step 4: Write `tests/conftest.py`**

```python
import pytest


@pytest.fixture
def sample_recipe_text():
    return """
    Bolo de Chocolate

    Ingredientes:
    - 2 xícaras de farinha de trigo
    - 1 xícara de açúcar
    - 1/2 xícara de cacau em pó
    - 3 ovos
    - 1 xícara de leite
    - 1/2 xícara de óleo

    Modo de preparo:
    1. Misture os ingredientes secos
    2. Adicione os ovos, leite e óleo
    3. Leve ao forno a 180 graus por 40 minutos

    Dica: use cacau 70% para um sabor mais intenso
    """
```

**Step 5: Install dependencies**

```bash
pip install -e ".[dev]"
playwright install chromium
```

> Note: `openai-whisper` requires `ffmpeg` installed on the system (`brew install ffmpeg` on macOS).

**Step 6: Commit**

```bash
git init
git add pyproject.toml .env.example src/ tests/ docs/
git commit -m "chore: initialize project structure"
```

---

## Task 2: RecipeModel

**Files:**
- Create: `src/models/recipe.py`
- Create: `tests/test_models.py`

**Step 1: Write failing test**

```python
# tests/test_models.py
from datetime import datetime
from src.models.recipe import Ingredient, RecipeContent, RecipeModel


def test_ingredient_all_fields():
    ing = Ingredient(quantity="2", unit="xícaras", name="farinha de trigo", notes="peneirada")
    assert ing.name == "farinha de trigo"
    assert ing.quantity == "2"


def test_ingredient_name_only():
    ing = Ingredient(name="sal a gosto")
    assert ing.quantity is None
    assert ing.unit is None
    assert ing.notes is None


def test_recipe_content_required_fields():
    content = RecipeContent(
        title="Bolo de Chocolate",
        ingredients=[Ingredient(name="farinha", quantity="2", unit="xícaras")],
        steps=["Misture tudo", "Asse por 40min"],
        extraction_confidence=0.95,
    )
    assert content.title == "Bolo de Chocolate"
    assert len(content.ingredients) == 1
    assert content.extraction_confidence == 0.95


def test_recipe_model_with_metadata():
    model = RecipeModel(
        title="Bolo",
        ingredients=[],
        steps=[],
        extraction_confidence=0.5,
        source_url="https://youtube.com/watch?v=abc",
        source_type="youtube",
    )
    assert model.source_type == "youtube"
    assert isinstance(model.extracted_at, datetime)


def test_recipe_model_json_serialization():
    model = RecipeModel(
        title="Bolo",
        ingredients=[Ingredient(name="farinha", quantity="2", unit="xícaras")],
        steps=["Passo 1"],
        extraction_confidence=0.9,
        source_url="https://example.com",
        source_type="web",
    )
    data = model.model_dump_json()
    assert "farinha" in data
    assert "Passo 1" in data


def test_to_markdown_contains_title_and_ingredients():
    model = RecipeModel(
        title="Bolo de Cenoura",
        ingredients=[Ingredient(name="cenoura", quantity="3", unit="unidades")],
        steps=["Bata no liquidificador", "Asse a 180 graus"],
        tips=["Não abra o forno antes de 30 min"],
        extraction_confidence=0.85,
        source_url="https://example.com",
        source_type="web",
    )
    md = model.to_markdown()
    assert "# Bolo de Cenoura" in md
    assert "cenoura" in md
    assert "Bata no liquidificador" in md
    assert "Não abra o forno" in md
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_models.py -v
```

Expected: `ImportError` — module not found

**Step 3: Write `src/models/recipe.py`**

```python
# src/models/recipe.py
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


class Ingredient(BaseModel):
    quantity: str | None = None
    unit: str | None = None
    name: str
    notes: str | None = None


class RecipeContent(BaseModel):
    """Fields extracted by the LLM."""
    title: str
    servings: str | None = None
    prep_time: str | None = None
    cook_time: str | None = None
    ingredients: list[Ingredient]
    steps: list[str]
    tips: list[str] = Field(default_factory=list)
    extraction_confidence: float = Field(ge=0.0, le=1.0)


class RecipeModel(RecipeContent):
    """Full model with source metadata."""
    source_url: str
    source_type: Literal["youtube", "instagram", "web"]
    extracted_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def to_markdown(self) -> str:
        lines = [
            f"# {self.title}",
            "",
            f"**Fonte:** {self.source_url}",
        ]
        if self.servings:
            lines.append(f"**Porções:** {self.servings}")
        if self.prep_time:
            lines.append(f"**Tempo de preparo:** {self.prep_time}")
        if self.cook_time:
            lines.append(f"**Tempo de cozimento:** {self.cook_time}")

        lines += ["", "## Ingredientes", ""]
        for ing in self.ingredients:
            parts = [p for p in [ing.quantity, ing.unit, ing.name] if p]
            line = " ".join(parts)
            if ing.notes:
                line += f" ({ing.notes})"
            lines.append(f"- {line}")

        lines += ["", "## Modo de Preparo", ""]
        for i, step in enumerate(self.steps, 1):
            lines.append(f"{i}. {step}")

        if self.tips:
            lines += ["", "## Dicas", ""]
            for tip in self.tips:
                lines.append(f"- {tip}")

        lines += [
            "",
            "---",
            f"*Confiança na extração: {self.extraction_confidence:.0%}*",
        ]
        return "\n".join(lines)
```

**Step 4: Run tests to verify they pass**

```bash
pytest tests/test_models.py -v
```

Expected: All 6 tests PASS

**Step 5: Commit**

```bash
git add src/models/recipe.py tests/test_models.py
git commit -m "feat: add RecipeContent and RecipeModel Pydantic models"
```

---

## Task 3: SourceRouter

**Files:**
- Create: `src/router.py`
- Create: `tests/test_router.py`

**Step 1: Write failing test**

```python
# tests/test_router.py
import pytest
from src.router import detect_source, UnsupportedSourceError


def test_youtube_watch_url():
    assert detect_source("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "youtube"


def test_youtube_short_url():
    assert detect_source("https://youtu.be/dQw4w9WgXcQ") == "youtube"


def test_youtube_shorts_url():
    assert detect_source("https://www.youtube.com/shorts/abc123") == "youtube"


def test_instagram_post_url():
    assert detect_source("https://www.instagram.com/p/ABC123/") == "instagram"


def test_instagram_reel_url():
    assert detect_source("https://www.instagram.com/reel/ABC123/") == "instagram"


def test_web_url():
    assert detect_source("https://www.tudogostoso.com.br/receita/123") == "web"


def test_http_web_url():
    assert detect_source("http://www.example.com/recipe") == "web"


def test_unsupported_url_raises():
    with pytest.raises(UnsupportedSourceError):
        detect_source("not-a-url")
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_router.py -v
```

Expected: `ImportError`

**Step 3: Write `src/router.py`**

```python
# src/router.py
import re
from typing import Literal

SourceType = Literal["youtube", "instagram", "web"]

_YOUTUBE_PATTERNS = [
    r"https?://(?:www\.)?youtube\.com/watch\?.*v=[\w-]+",
    r"https?://(?:www\.)?youtu\.be/[\w-]+",
    r"https?://(?:www\.)?youtube\.com/shorts/[\w-]+",
]

_INSTAGRAM_PATTERNS = [
    r"https?://(?:www\.)?instagram\.com/p/[\w-]+",
    r"https?://(?:www\.)?instagram\.com/reel/[\w-]+",
]


class UnsupportedSourceError(Exception):
    pass


def detect_source(url: str) -> SourceType:
    for pattern in _YOUTUBE_PATTERNS:
        if re.search(pattern, url):
            return "youtube"
    for pattern in _INSTAGRAM_PATTERNS:
        if re.search(pattern, url):
            return "instagram"
    if url.startswith("http"):
        return "web"
    raise UnsupportedSourceError(f"URL não reconhecida: {url}")
```

**Step 4: Run tests to verify they pass**

```bash
pytest tests/test_router.py -v
```

Expected: All 8 tests PASS

**Step 5: Commit**

```bash
git add src/router.py tests/test_router.py
git commit -m "feat: add SourceRouter with URL pattern detection"
```

---

## Task 4: LLM Agent

**Files:**
- Create: `src/llm.py`
- Create: `tests/test_llm.py`

**Step 1: Write failing test**

```python
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
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_llm.py -v
```

Expected: `ImportError`

**Step 3: Write `src/llm.py`**

```python
# src/llm.py
import os

from dotenv import load_dotenv
from pydantic_ai import Agent, BinaryContent
from pydantic_ai.models.openai import OpenAIModel

from src.models.recipe import RecipeContent, RecipeModel

load_dotenv()

_SYSTEM_PROMPT = """Você é um especialista em extração de receitas culinárias.
Dado um texto (ou imagem) de uma receita, extraia todas as informações e retorne em formato estruturado.

Regras:
- Extraia TODOS os ingredientes com quantidades e unidades exatas
- Extraia as instruções passo a passo
- Coloque dicas, variações e observações do chef em "tips"
- Se uma informação estiver ausente, use null
- Defina extraction_confidence entre 0.0 e 1.0 indicando a clareza da receita
- Se não encontrar receita, use extraction_confidence=0.0 e listas vazias
- Responda sempre em português"""

_MAX_TEXT_LENGTH = 12_000  # ~3k tokens


def create_recipe_agent() -> Agent:
    model = OpenAIModel(
        model_name=os.getenv("OPENROUTER_MODEL", "openai/gpt-4o"),
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENROUTER_API_KEY", ""),
    )
    return Agent(
        model=model,
        result_type=RecipeContent,
        system_prompt=_SYSTEM_PROMPT,
    )


_agent = create_recipe_agent()


def extract_recipe_from_text(
    text: str,
    source_url: str,
    source_type: str,
) -> RecipeModel:
    truncated = text[:_MAX_TEXT_LENGTH]
    result = _agent.run_sync(f"Extraia a receita do seguinte conteúdo:\n\n{truncated}")
    content = result.data
    return RecipeModel(
        **content.model_dump(),
        source_url=source_url,
        source_type=source_type,
    )


def extract_recipe_from_images(
    images: list[bytes],
    caption: str,
    source_url: str,
    source_type: str,
) -> RecipeModel:
    parts: list = [f"Caption do post: {caption}\n\nExtraia a receita das imagens abaixo:"]
    for img_bytes in images:
        parts.append(BinaryContent(data=img_bytes, media_type="image/jpeg"))
    result = _agent.run_sync(parts)
    content = result.data
    return RecipeModel(
        **content.model_dump(),
        source_url=source_url,
        source_type=source_type,
    )
```

**Step 4: Run tests to verify they pass**

```bash
pytest tests/test_llm.py -v
```

Expected: All 4 tests PASS

**Step 5: Commit**

```bash
git add src/llm.py tests/test_llm.py
git commit -m "feat: add LLM agent with OpenRouter/Pydantic AI integration"
```

---

## Task 5: YouTube Extractor

**Files:**
- Create: `src/extractors/youtube_transcript.py`
- Create: `tests/test_youtube_extractor.py`

**Step 1: Write failing test**

```python
# tests/test_youtube_extractor.py
import pytest
from unittest.mock import patch, AsyncMock

from src.extractors.youtube_transcript import YouTubeExtractor, extract_video_id


def test_extract_video_id_watch_url():
    assert extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"


def test_extract_video_id_short_url():
    assert extract_video_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"


def test_extract_video_id_shorts():
    assert extract_video_id("https://www.youtube.com/shorts/abc123") == "abc123"


def test_extract_video_id_invalid_raises():
    with pytest.raises(ValueError):
        extract_video_id("https://www.example.com")


@pytest.mark.asyncio
async def test_extract_text_uses_transcript_api():
    extractor = YouTubeExtractor()
    with patch(
        "src.extractors.youtube_transcript.YouTubeTranscriptApi.get_transcript",
        return_value=[
            {"text": "Hoje vou fazer um bolo", "start": 0.0},
            {"text": "com 2 xícaras de farinha", "start": 2.0},
        ],
    ):
        text = await extractor.extract_text("https://www.youtube.com/watch?v=abc123")

    assert "bolo" in text
    assert "farinha" in text


@pytest.mark.asyncio
async def test_extract_text_falls_back_to_description():
    from youtube_transcript_api import TranscriptsDisabled

    extractor = YouTubeExtractor()
    with patch(
        "src.extractors.youtube_transcript.YouTubeTranscriptApi.get_transcript",
        side_effect=TranscriptsDisabled("abc123"),
    ):
        with patch.object(
            extractor,
            "_get_description",
            return_value="Receita de bolo: ingredientes e modo de preparo detalhado aqui...",
        ):
            text = await extractor.extract_text("https://www.youtube.com/watch?v=abc123")

    assert "bolo" in text


@pytest.mark.asyncio
async def test_extract_text_falls_back_to_whisper():
    from youtube_transcript_api import TranscriptsDisabled

    extractor = YouTubeExtractor()
    with patch(
        "src.extractors.youtube_transcript.YouTubeTranscriptApi.get_transcript",
        side_effect=TranscriptsDisabled("abc123"),
    ):
        with patch.object(extractor, "_get_description", return_value=""):
            with patch.object(
                extractor,
                "_whisper_transcribe",
                new_callable=AsyncMock,
                return_value="Bolo de chocolate com farinha",
            ):
                text = await extractor.extract_text("https://www.youtube.com/watch?v=abc123")

    assert text == "Bolo de chocolate com farinha"
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_youtube_extractor.py -v
```

Expected: `ImportError`

**Step 3: Write `src/extractors/youtube_transcript.py`**

```python
# src/extractors/youtube_transcript.py
import asyncio
import logging
import os
import re
import tempfile
from pathlib import Path

from youtube_transcript_api import YouTubeTranscriptApi

logger = logging.getLogger(__name__)


def extract_video_id(url: str) -> str:
    patterns = [
        r"youtube\.com/watch\?.*v=([\w-]+)",
        r"youtu\.be/([\w-]+)",
        r"youtube\.com/shorts/([\w-]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    raise ValueError(f"Não foi possível extrair ID do vídeo de: {url}")


class YouTubeExtractor:
    def __init__(self, whisper_model_size: str | None = None):
        self.whisper_model_size = whisper_model_size or os.getenv("WHISPER_MODEL_SIZE", "base")
        self._whisper_model = None  # lazy load

    async def extract_text(self, url: str) -> str:
        video_id = extract_video_id(url)

        # Strategy 1: Transcript API
        try:
            transcript = await asyncio.to_thread(
                YouTubeTranscriptApi.get_transcript, video_id, languages=["pt", "en"]
            )
            text = " ".join(entry["text"] for entry in transcript)
            logger.info("YouTube: extraído via API de legendas")
            return text
        except Exception as e:
            logger.warning(f"YouTube transcript API falhou: {e}")

        # Strategy 2: Video description
        try:
            desc = await asyncio.to_thread(self._get_description, url)
            if desc and len(desc.strip()) > 100:
                logger.info("YouTube: extraído via descrição do vídeo")
                return desc
        except Exception as e:
            logger.warning(f"YouTube descrição falhou: {e}")

        # Strategy 3: Whisper
        logger.info("YouTube: fallback para transcrição Whisper")
        return await self._whisper_transcribe(url)

    def _get_description(self, url: str) -> str:
        import yt_dlp

        opts = {"quiet": True, "no_warnings": True, "skip_download": True}
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return info.get("description", "")

    async def _whisper_transcribe(self, url: str) -> str:
        import whisper
        import yt_dlp

        if self._whisper_model is None:
            self._whisper_model = await asyncio.to_thread(
                whisper.load_model, self.whisper_model_size
            )

        with tempfile.TemporaryDirectory() as tmpdir:
            audio_template = str(Path(tmpdir) / "audio.%(ext)s")
            opts = {
                "format": "bestaudio/best",
                "outtmpl": audio_template,
                "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3"}],
                "quiet": True,
            }
            await asyncio.to_thread(self._download_audio, url, opts)
            mp3_path = str(Path(tmpdir) / "audio.mp3")
            result = await asyncio.to_thread(self._whisper_model.transcribe, mp3_path)
            return result["text"]

    @staticmethod
    def _download_audio(url: str, opts: dict) -> None:
        import yt_dlp

        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])
```

**Step 4: Run tests to verify they pass**

```bash
pytest tests/test_youtube_extractor.py -v
```

Expected: All 7 tests PASS

**Step 5: Commit**

```bash
git add src/extractors/youtube_transcript.py tests/test_youtube_extractor.py
git commit -m "feat: add YouTubeExtractor with transcript/description/whisper strategies"
```

---

## Task 6: YouTube Agent

**Files:**
- Create: `src/agents/base.py`
- Create: `src/agents/youtube.py`
- Create: `tests/test_youtube_agent.py`

**Step 1: Write failing test**

```python
# tests/test_youtube_agent.py
import pytest
from unittest.mock import AsyncMock, patch

from src.agents.youtube import YouTubeAgent
from src.models.recipe import Ingredient, RecipeModel


@pytest.fixture
def mock_recipe():
    return RecipeModel(
        title="Bolo de Chocolate",
        ingredients=[Ingredient(name="farinha", quantity="2", unit="xícaras")],
        steps=["Passo 1"],
        extraction_confidence=0.9,
        source_url="https://youtube.com/watch?v=abc",
        source_type="youtube",
    )


@pytest.mark.asyncio
async def test_youtube_agent_extract_returns_recipe(mock_recipe):
    agent = YouTubeAgent()
    with patch.object(agent.extractor, "extract_text", new_callable=AsyncMock, return_value="texto da receita"):
        with patch("src.agents.youtube.extract_recipe_from_text", return_value=mock_recipe):
            result = await agent.extract("https://youtube.com/watch?v=abc")

    assert isinstance(result, RecipeModel)
    assert result.source_type == "youtube"
    assert result.title == "Bolo de Chocolate"


@pytest.mark.asyncio
async def test_youtube_agent_passes_correct_source_type(mock_recipe):
    agent = YouTubeAgent()
    url = "https://youtube.com/watch?v=abc"
    with patch.object(agent.extractor, "extract_text", new_callable=AsyncMock, return_value="texto"):
        with patch("src.agents.youtube.extract_recipe_from_text", return_value=mock_recipe) as mock_fn:
            await agent.extract(url)

    _, kwargs = mock_fn.call_args
    assert kwargs["source_type"] == "youtube"
    assert kwargs["source_url"] == url
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_youtube_agent.py -v
```

Expected: `ImportError`

**Step 3: Write `src/agents/base.py`**

```python
# src/agents/base.py
from abc import ABC, abstractmethod

from src.models.recipe import RecipeModel


class BaseAgent(ABC):
    @abstractmethod
    async def extract(self, url: str) -> RecipeModel:
        """Extrai a receita da URL fornecida."""
        ...
```

**Step 4: Write `src/agents/youtube.py`**

```python
# src/agents/youtube.py
from src.agents.base import BaseAgent
from src.extractors.youtube_transcript import YouTubeExtractor
from src.llm import extract_recipe_from_text
from src.models.recipe import RecipeModel


class YouTubeAgent(BaseAgent):
    def __init__(self):
        self.extractor = YouTubeExtractor()

    async def extract(self, url: str) -> RecipeModel:
        text = await self.extractor.extract_text(url)
        return extract_recipe_from_text(
            text=text,
            source_url=url,
            source_type="youtube",
        )
```

**Step 5: Run tests to verify they pass**

```bash
pytest tests/test_youtube_agent.py -v
```

Expected: All 2 tests PASS

**Step 6: Commit**

```bash
git add src/agents/base.py src/agents/youtube.py tests/test_youtube_agent.py
git commit -m "feat: add BaseAgent and YouTubeAgent"
```

---

## Task 7: Instagram Extractor

**Files:**
- Create: `src/extractors/instagram_loader.py`
- Create: `tests/test_instagram_extractor.py`

**Step 1: Write failing test**

```python
# tests/test_instagram_extractor.py
import pytest
from unittest.mock import MagicMock, patch

from src.extractors.instagram_loader import InstagramExtractor, extract_shortcode


def test_extract_shortcode_post():
    assert extract_shortcode("https://www.instagram.com/p/ABC123/") == "ABC123"


def test_extract_shortcode_reel():
    assert extract_shortcode("https://www.instagram.com/reel/XYZ789/") == "XYZ789"


def test_extract_shortcode_invalid_raises():
    with pytest.raises(ValueError):
        extract_shortcode("https://www.instagram.com/user/")


def test_extract_returns_caption_when_present():
    extractor = InstagramExtractor()
    mock_post = MagicMock()
    mock_post.caption = "Bolo de chocolate incrível! Ingredientes: 2 xícaras de farinha, modo de preparo abaixo..."
    mock_post.typename = "GraphImage"

    with patch("src.extractors.instagram_loader.instaloader.Post.from_shortcode", return_value=mock_post):
        result = extractor.extract("https://www.instagram.com/p/ABC123/")

    assert result["text"] == mock_post.caption
    assert result["images"] == []


def test_extract_fetches_images_when_caption_short():
    extractor = InstagramExtractor()
    mock_post = MagicMock()
    mock_post.caption = "Receita"  # abaixo do mínimo
    mock_post.typename = "GraphImage"

    fake_image_bytes = b"fake_jpeg_bytes"

    with patch("src.extractors.instagram_loader.instaloader.Post.from_shortcode", return_value=mock_post):
        with patch.object(extractor, "_download_images", return_value=[fake_image_bytes]):
            result = extractor.extract("https://www.instagram.com/p/ABC123/")

    assert len(result["images"]) == 1
    assert result["images"][0] == fake_image_bytes
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_instagram_extractor.py -v
```

Expected: `ImportError`

**Step 3: Write `src/extractors/instagram_loader.py`**

```python
# src/extractors/instagram_loader.py
import logging
import os
import re
import tempfile
from pathlib import Path

import instaloader

logger = logging.getLogger(__name__)

_CAPTION_MIN_LENGTH = 50


def extract_shortcode(url: str) -> str:
    match = re.search(r"instagram\.com/(?:p|reel)/([\w-]+)", url)
    if not match:
        raise ValueError(f"Não foi possível extrair shortcode de: {url}")
    return match.group(1)


class InstagramExtractor:
    def __init__(
        self,
        username: str | None = None,
        password: str | None = None,
    ):
        self._loader = instaloader.Instaloader(quiet=True)
        username = username or os.getenv("INSTAGRAM_USERNAME")
        password = password or os.getenv("INSTAGRAM_PASSWORD")
        if username and password:
            try:
                self._loader.login(username, password)
            except Exception as e:
                logger.warning(f"Instagram login falhou: {e}")

    def extract(self, url: str) -> dict:
        """Retorna {'text': caption, 'images': [bytes, ...]}"""
        shortcode = extract_shortcode(url)
        post = instaloader.Post.from_shortcode(self._loader.context, shortcode)
        caption = post.caption or ""
        result: dict = {"text": caption, "images": []}

        if len(caption.strip()) < _CAPTION_MIN_LENGTH:
            logger.info("Instagram: caption curta, baixando imagens para visão")
            result["images"] = self._download_images(post)

        return result

    def _download_images(self, post) -> list[bytes]:
        images = []
        with tempfile.TemporaryDirectory() as tmpdir:
            self._loader.download_post(post, target=Path(tmpdir))
            for img_file in sorted(Path(tmpdir).glob("*.jpg")):
                images.append(img_file.read_bytes())
        return images
```

**Step 4: Run tests to verify they pass**

```bash
pytest tests/test_instagram_extractor.py -v
```

Expected: All 5 tests PASS

**Step 5: Commit**

```bash
git add src/extractors/instagram_loader.py tests/test_instagram_extractor.py
git commit -m "feat: add InstagramExtractor with caption and image download"
```

---

## Task 8: Instagram Agent

**Files:**
- Create: `src/agents/instagram.py`
- Create: `tests/test_instagram_agent.py`

**Step 1: Write failing test**

```python
# tests/test_instagram_agent.py
import pytest
from unittest.mock import patch, MagicMock

from src.agents.instagram import InstagramAgent
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
        "text": "Bolo delicioso! Ingredientes: 2 xícaras de farinha, açúcar e ovos...",
        "images": [],
    }

    with patch.object(agent.extractor, "extract", return_value=extracted):
        with patch("src.agents.instagram.extract_recipe_from_text", return_value=mock_recipe) as mock_fn:
            result = await agent.extract(url)

    mock_fn.assert_called_once()
    assert result.source_type == "instagram"


@pytest.mark.asyncio
async def test_instagram_agent_uses_vision_when_images_present(mock_recipe):
    agent = InstagramAgent()
    url = "https://www.instagram.com/p/ABC123/"
    extracted = {"text": "Yummy!", "images": [b"fake_image_bytes"]}

    with patch.object(agent.extractor, "extract", return_value=extracted):
        with patch("src.agents.instagram.extract_recipe_from_images", return_value=mock_recipe) as mock_fn:
            result = await agent.extract(url)

    mock_fn.assert_called_once()
    assert result.source_type == "instagram"
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_instagram_agent.py -v
```

Expected: `ImportError`

**Step 3: Write `src/agents/instagram.py`**

```python
# src/agents/instagram.py
import asyncio

from src.agents.base import BaseAgent
from src.extractors.instagram_loader import InstagramExtractor
from src.llm import extract_recipe_from_images, extract_recipe_from_text
from src.models.recipe import RecipeModel


class InstagramAgent(BaseAgent):
    def __init__(self):
        self.extractor = InstagramExtractor()

    async def extract(self, url: str) -> RecipeModel:
        extracted = await asyncio.to_thread(self.extractor.extract, url)
        text = extracted["text"]
        images = extracted["images"]

        if images:
            return extract_recipe_from_images(
                images=images,
                caption=text,
                source_url=url,
                source_type="instagram",
            )

        return extract_recipe_from_text(
            text=text,
            source_url=url,
            source_type="instagram",
        )
```

**Step 4: Run tests to verify they pass**

```bash
pytest tests/test_instagram_agent.py -v
```

Expected: All 2 tests PASS

**Step 5: Commit**

```bash
git add src/agents/instagram.py tests/test_instagram_agent.py
git commit -m "feat: add InstagramAgent with text and vision paths"
```

---

## Task 9: Web Scraper

**Files:**
- Create: `src/extractors/web_scraper.py`
- Create: `tests/test_web_scraper.py`

**Step 1: Write failing test**

```python
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
  <p>Ingredientes: 2 xícaras de farinha de trigo</p>
  <p>Modo de preparo: Misture tudo e asse a 180 graus.</p>
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

    with patch("httpx.AsyncClient") as mock_client:
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

    with patch.object(scraper, "_scrape_httpx", return_value="curto"):
        with patch.object(
            scraper,
            "_scrape_playwright",
            new_callable=AsyncMock,
            return_value="Conteúdo completo da receita com ingredientes e modo de preparo detalhado",
        ):
            text = await scraper.scrape("https://example.com/receita")

    assert "ingredientes" in text
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_web_scraper.py -v
```

Expected: `ImportError`

**Step 3: Write `src/extractors/web_scraper.py`**

```python
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
```

**Step 4: Run tests to verify they pass**

```bash
pytest tests/test_web_scraper.py -v
```

Expected: All 3 tests PASS

**Step 5: Commit**

```bash
git add src/extractors/web_scraper.py tests/test_web_scraper.py
git commit -m "feat: add WebScraper with httpx and Playwright fallback"
```

---

## Task 10: Web Agent

**Files:**
- Create: `src/agents/web.py`
- Create: `tests/test_web_agent.py`

**Step 1: Write failing test**

```python
# tests/test_web_agent.py
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

    with patch.object(agent.scraper, "scrape", new_callable=AsyncMock, return_value="Texto da receita..."):
        with patch("src.agents.web.extract_recipe_from_text", return_value=mock_recipe):
            result = await agent.extract(url)

    assert isinstance(result, RecipeModel)
    assert result.source_type == "web"


@pytest.mark.asyncio
async def test_web_agent_passes_correct_args(mock_recipe):
    agent = WebAgent()
    url = "https://example.com/receita"

    with patch.object(agent.scraper, "scrape", new_callable=AsyncMock, return_value="texto"):
        with patch("src.agents.web.extract_recipe_from_text", return_value=mock_recipe) as mock_fn:
            await agent.extract(url)

    _, kwargs = mock_fn.call_args
    assert kwargs["source_url"] == url
    assert kwargs["source_type"] == "web"
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_web_agent.py -v
```

Expected: `ImportError`

**Step 3: Write `src/agents/web.py`**

```python
# src/agents/web.py
from src.agents.base import BaseAgent
from src.extractors.web_scraper import WebScraper
from src.llm import extract_recipe_from_text
from src.models.recipe import RecipeModel


class WebAgent(BaseAgent):
    def __init__(self):
        self.scraper = WebScraper()

    async def extract(self, url: str) -> RecipeModel:
        text = await self.scraper.scrape(url)
        return extract_recipe_from_text(
            text=text,
            source_url=url,
            source_type="web",
        )
```

**Step 4: Run tests to verify they pass**

```bash
pytest tests/test_web_agent.py -v
```

Expected: All 2 tests PASS

**Step 5: Commit**

```bash
git add src/agents/web.py tests/test_web_agent.py
git commit -m "feat: add WebAgent"
```

---

## Task 11: CLI Entry Point

**Files:**
- Create: `src/main.py`
- Create: `tests/test_main.py`

**Step 1: Write failing test**

```python
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
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_main.py -v
```

Expected: `ImportError`

**Step 3: Write `src/main.py`**

```python
# src/main.py
import asyncio
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from src.agents.instagram import InstagramAgent
from src.agents.web import WebAgent
from src.agents.youtube import YouTubeAgent
from src.models.recipe import RecipeModel
from src.router import UnsupportedSourceError, detect_source

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

_AGENTS = {
    "youtube": YouTubeAgent,
    "instagram": InstagramAgent,
    "web": WebAgent,
}


async def run(url: str) -> RecipeModel:
    source = detect_source(url)
    logger.info(f"Fonte detectada: {source} — {url}")
    agent = _AGENTS[source]()
    return await agent.extract(url)


def save_outputs(recipe: RecipeModel, output_dir: Path = Path(".")) -> None:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    base_name = f"recipe_{timestamp}"

    json_path = output_dir / f"{base_name}.json"
    json_path.write_text(recipe.model_dump_json(indent=2), encoding="utf-8")
    logger.info(f"JSON salvo: {json_path}")

    md_path = output_dir / f"{base_name}.md"
    md_path.write_text(recipe.to_markdown(), encoding="utf-8")
    logger.info(f"Markdown salvo: {md_path}")


def main() -> None:
    if len(sys.argv) < 2:
        print("Uso: python -m src.main <URL>")
        sys.exit(1)

    url = sys.argv[1]
    try:
        recipe = asyncio.run(run(url))
        save_outputs(recipe)
        print(f"\nReceita extraída: {recipe.title}")
        print(f"  Confiança: {recipe.extraction_confidence:.0%}")
        print(f"  Ingredientes: {len(recipe.ingredients)}")
        print(f"  Passos: {len(recipe.steps)}")
    except UnsupportedSourceError as e:
        print(f"Erro: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        logger.error(f"Falha na extração: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
```

**Step 4: Run all tests**

```bash
pytest -v
```

Expected: All tests PASS

**Step 5: Commit**

```bash
git add src/main.py tests/test_main.py
git commit -m "feat: add CLI entry point with JSON and Markdown output"
```

---

## Task 12: Smoke Test (requer `.env` configurado com chave real)

> Este passo faz chamadas reais à internet e à API do OpenRouter. Configure o `.env` primeiro.

**Step 1: Configurar `.env`**

```bash
cp .env.example .env
# Editar .env: adicionar OPENROUTER_API_KEY
```

**Step 2: Testar extração de site web**

```bash
python -m src.main "https://www.tudogostoso.com.br/receita/1-bolo-de-mel.html"
```

Expected:
- Arquivo `recipe_<timestamp>.json` criado com ingredientes e passos
- Arquivo `recipe_<timestamp>.md` criado e legível

**Step 3: Testar extração do YouTube**

```bash
python -m src.main "https://www.youtube.com/watch?v=<video_id_com_receita>"
```

Expected: mesma saída estruturada

**Step 4: Verificar campos do JSON**

```bash
cat recipe_*.json | python -m json.tool
```

Expected: campos `title`, `ingredients`, `steps`, `extraction_confidence` preenchidos

---

## Fora do Escopo (MVP)

- Interface web ou API REST
- Banco de dados / persistência
- Autenticação de usuário
- Extração de áudio de Reels do Instagram
- Suporte a TikTok, Pinterest, etc.
- Cache de resultados
