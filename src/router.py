# src/router.py
"""
Roteador de URLs: determina a fonte de uma URL e retorna o tipo correspondente.

O roteamento é baseado em regex:
  - YouTube: youtube.com/watch, youtu.be, youtube.com/shorts
  - Instagram: instagram.com/p/, instagram.com/reel/
  - Web: qualquer URL http(s) que não seja YouTube nem Instagram

URLs que não começam com http(s) levantam `UnsupportedSourceError`.
"""
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
    """Levantada quando a URL não corresponde a nenhuma fonte suportada."""
    pass


def detect_source(url: str) -> SourceType:
    """Retorna o tipo de fonte ('youtube', 'instagram' ou 'web') para a URL dada."""
    for pattern in _YOUTUBE_PATTERNS:
        if re.search(pattern, url):
            return "youtube"
    for pattern in _INSTAGRAM_PATTERNS:
        if re.search(pattern, url):
            return "instagram"
    if url.startswith("http"):
        return "web"
    raise UnsupportedSourceError(f"URL não reconhecida: {url}")
