# tests/test_instagram_extractor.py
"""Testes unitários do InstagramExtractor.

Cobre todas as ramificações da cascata de extração:
- `extract_shortcode`: parse de URLs post e reel, erro em URL inválida
- `_extract_via_instaloader`: caption longa, caption curta → imagens, vídeo → Whisper
- Fallback quando instaloader falha: og:description + yt-dlp + Whisper
- Fallback final: só og:description quando yt-dlp também falha

Nenhum teste faz chamadas reais ao Instagram, yt-dlp ou Whisper.
"""
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
    mock_post.is_video = False

    with patch("src.extractors.instagram_loader.instaloader.Post.from_shortcode", return_value=mock_post):
        result = extractor.extract("https://www.instagram.com/p/ABC123/")

    assert result["text"] == mock_post.caption
    assert result["images"] == []


def test_extract_fetches_images_when_caption_short():
    extractor = InstagramExtractor()
    mock_post = MagicMock()
    mock_post.caption = "Receita"  # abaixo do mínimo
    mock_post.is_video = False

    fake_image_bytes = b"fake_jpeg_bytes"

    with patch("src.extractors.instagram_loader.instaloader.Post.from_shortcode", return_value=mock_post):
        with patch.object(extractor, "_download_images", return_value=[fake_image_bytes]):
            result = extractor.extract("https://www.instagram.com/p/ABC123/")

    assert len(result["images"]) == 1
    assert result["images"][0] == fake_image_bytes


def test_extract_transcribes_video_when_post_is_video():
    extractor = InstagramExtractor()
    mock_post = MagicMock()
    mock_post.caption = "Steak Au Poivre recipe!"
    mock_post.is_video = True

    with patch("src.extractors.instagram_loader.instaloader.Post.from_shortcode", return_value=mock_post):
        with patch.object(extractor, "_transcribe_video", return_value="Add butter and cream to the pan..."):
            result = extractor.extract("https://www.instagram.com/p/ABC123/")

    assert "Steak Au Poivre recipe!" in result["text"]
    assert "Add butter and cream to the pan..." in result["text"]
    assert result["images"] == []


def test_extract_falls_back_to_ytdlp_whisper_when_instaloader_fails():
    extractor = InstagramExtractor()
    url = "https://www.instagram.com/p/ABC123/"

    with patch("src.extractors.instagram_loader.instaloader.Post.from_shortcode", side_effect=Exception("403")):
        with patch("src.extractors.instagram_loader._fetch_og_description", return_value="Steak Au Poivre description."):
            with patch.object(extractor, "_transcribe_video", return_value="Add flour and butter..."):
                result = extractor.extract(url)

    assert "Steak Au Poivre description." in result["text"]
    assert "Add flour and butter..." in result["text"]
    assert result["images"] == []


def test_extract_falls_back_to_og_description_when_ytdlp_fails():
    extractor = InstagramExtractor()
    url = "https://www.instagram.com/p/ABC123/"

    with patch("src.extractors.instagram_loader.instaloader.Post.from_shortcode", side_effect=Exception("403")):
        with patch("src.extractors.instagram_loader._fetch_og_description", return_value="Receita: misture tudo."):
            with patch.object(extractor, "_transcribe_video", side_effect=Exception("no video")):
                result = extractor.extract(url)

    assert result["text"] == "Receita: misture tudo."
    assert result["images"] == []
