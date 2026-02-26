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
