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
