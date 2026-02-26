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
