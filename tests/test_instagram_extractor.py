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
