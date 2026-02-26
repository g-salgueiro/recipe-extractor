# tests/test_youtube_extractor.py
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
            "_get_description",
            return_value="Receita de bolo de chocolate: ingredientes incluem 2 xícaras de farinha de trigo, 1 xícara de açúcar e 3 ovos.",
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
        with patch.object(extractor, "_get_description", return_value=""):
            with patch.object(
                extractor,
                "_whisper_transcribe",
                new_callable=AsyncMock,
                return_value="Bolo de chocolate com farinha",
            ):
                text = await extractor.extract_text("https://www.youtube.com/watch?v=abc123")

    assert text == "Bolo de chocolate com farinha"
