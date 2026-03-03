# tests/test_youtube_extractor.py
"""Testes unitários do YouTubeExtractor.

Verifica `extract_video_id` para os três formatos de URL do YouTube,
as três estratégias de `extract_text` (via `extract_sources`), e o
método `extract_sources` diretamente.
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

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


# --- extract_text (legacy wrapper) ---


@pytest.mark.asyncio
async def test_extract_text_uses_transcript_api():
    extractor = YouTubeExtractor()

    snippet1 = MagicMock()
    snippet1.text = "Hoje vou fazer um bolo"
    snippet2 = MagicMock()
    snippet2.text = "com 2 xícaras de farinha"

    with patch(
        "src.extractors.youtube_transcript.YouTubeTranscriptApi.fetch",
        return_value=[snippet1, snippet2],
    ):
        with patch.object(extractor, "_get_metadata", return_value=("Titulo", "")):
            text = await extractor.extract_text("https://www.youtube.com/watch?v=abc123")

    assert "bolo" in text
    assert "farinha" in text


@pytest.mark.asyncio
async def test_extract_text_falls_back_to_description():
    from youtube_transcript_api import TranscriptsDisabled

    extractor = YouTubeExtractor()
    with patch(
        "src.extractors.youtube_transcript.YouTubeTranscriptApi.fetch",
        side_effect=TranscriptsDisabled("abc123"),
    ):
        with patch.object(
            extractor,
            "_get_metadata",
            return_value=("Titulo", "Receita de bolo de chocolate: ingredientes incluem 2 xícaras de farinha de trigo, 1 xícara de açúcar e 3 ovos."),
        ):
            text = await extractor.extract_text("https://www.youtube.com/watch?v=abc123")

    assert "bolo" in text


@pytest.mark.asyncio
async def test_extract_text_falls_back_to_whisper():
    from youtube_transcript_api import TranscriptsDisabled

    extractor = YouTubeExtractor()
    with patch(
        "src.extractors.youtube_transcript.YouTubeTranscriptApi.fetch",
        side_effect=TranscriptsDisabled("abc123"),
    ):
        with patch.object(extractor, "_get_metadata", return_value=("", "")):
            with patch.object(
                extractor,
                "_whisper_transcribe",
                new_callable=AsyncMock,
                return_value="Bolo de chocolate com farinha",
            ):
                text = await extractor.extract_text("https://www.youtube.com/watch?v=abc123")

    assert "Bolo de chocolate com farinha" in text


# --- extract_sources ---


@pytest.mark.asyncio
async def test_extract_sources_returns_transcript_and_metadata():
    extractor = YouTubeExtractor()
    snippet1 = MagicMock()
    snippet1.text = "Hoje vou fazer um bolo"
    snippet2 = MagicMock()
    snippet2.text = "com 2 xícaras de farinha"

    with patch("src.extractors.youtube_transcript.YouTubeTranscriptApi.fetch", return_value=[snippet1, snippet2]):
        with patch.object(extractor, "_get_metadata", return_value=("Bolo de Chocolate", "Ingredientes: 2 xícaras de farinha, 1 de açúcar, modo de preparo detalhado aqui com mais de cem caracteres para passar do threshold.")):
            sources = await extractor.extract_sources("https://www.youtube.com/watch?v=abc123")

    assert "legenda" in sources
    assert "descricao" in sources
    assert "titulo" in sources
    assert "bolo" in sources["legenda"]
    assert "farinha" in sources["descricao"]


@pytest.mark.asyncio
async def test_extract_sources_skips_short_description():
    extractor = YouTubeExtractor()
    snippet = MagicMock()
    snippet.text = "Receita"

    with patch("src.extractors.youtube_transcript.YouTubeTranscriptApi.fetch", return_value=[snippet]):
        with patch.object(extractor, "_get_metadata", return_value=("Titulo", "Curta")):
            sources = await extractor.extract_sources("https://www.youtube.com/watch?v=abc123")

    assert "legenda" in sources
    assert "descricao" not in sources
    assert "titulo" in sources


@pytest.mark.asyncio
async def test_extract_sources_uses_whisper_when_no_transcript_no_description():
    from youtube_transcript_api import TranscriptsDisabled
    extractor = YouTubeExtractor()

    with patch("src.extractors.youtube_transcript.YouTubeTranscriptApi.fetch", side_effect=TranscriptsDisabled("abc123")):
        with patch.object(extractor, "_get_metadata", return_value=("Titulo", "")):
            with patch.object(extractor, "_whisper_transcribe", new_callable=AsyncMock, return_value="Transcrição Whisper"):
                sources = await extractor.extract_sources("https://www.youtube.com/watch?v=abc123")

    assert "transcricao_whisper" in sources
    assert sources["transcricao_whisper"] == "Transcrição Whisper"


@pytest.mark.asyncio
async def test_extract_sources_no_whisper_when_transcript_exists():
    extractor = YouTubeExtractor()
    snippet = MagicMock()
    snippet.text = "Receita de bolo"

    with patch("src.extractors.youtube_transcript.YouTubeTranscriptApi.fetch", return_value=[snippet]):
        with patch.object(extractor, "_get_metadata", return_value=("Titulo", "")):
            with patch.object(extractor, "_whisper_transcribe", new_callable=AsyncMock) as mock_whisper:
                await extractor.extract_sources("https://www.youtube.com/watch?v=abc123")

    mock_whisper.assert_not_called()
