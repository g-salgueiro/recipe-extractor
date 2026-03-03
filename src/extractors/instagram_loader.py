# src/extractors/instagram_loader.py
"""
Extrator de conteúdo de posts do Instagram com cascata de fallbacks.

Estratégias em ordem de prioridade:

1. **instaloader** — acessa o post diretamente.
   - Post de foto com caption longa (≥ 50 chars): retorna texto.
   - Post de foto com caption curta (< 50 chars): baixa imagens para visão LLM.
   - Post de vídeo (`post.is_video`): transcreve o áudio via yt-dlp + Whisper.

2. **og:description via httpx** — quando instaloader falha (tipicamente 403
   sem credenciais). Extrai o conteúdo do meta tag `og:description` da página
   pública. Requer `re.DOTALL` pois o atributo HTML contém quebras de linha.

3. **yt-dlp + Whisper** — quando os dois anteriores falham ou retornam texto
   sem receita (e.g. post de vídeo onde instaloader não conseguiu acessar a API).
   O download é síncrono porque este método é chamado de dentro de uma thread
   (via `asyncio.to_thread` no `InstagramAgent`).

Issue conhecido: comentários do owner não são verificados (ver docs/known-issues.md).
"""
import logging
import os
import re
import tempfile
from pathlib import Path

import httpx
import instaloader

logger = logging.getLogger(__name__)

_CAPTION_MIN_LENGTH = 50


def extract_shortcode(url: str) -> str:
    """Extrai o shortcode de uma URL de post ou reel do Instagram."""
    match = re.search(r"instagram\.com/(?:p|reel)/([\w-]+)", url)
    if not match:
        raise ValueError(f"Não foi possível extrair shortcode de: {url}")
    return match.group(1)


def _fetch_og_description(url: str) -> str:
    """Extrai o conteúdo do meta tag og:description via httpx (sem autenticação).

    Usa `re.DOTALL` porque o atributo `content` do Instagram contém quebras
    de linha literais, e sem essa flag o `(.*?)` para no primeiro `\\n`.
    Aplica `html.unescape()` para decodificar entidades HTML (&quot;, &#x2022;, etc.).
    """
    try:
        from html import unescape
        headers = {"User-Agent": "Mozilla/5.0 (compatible; RecipeBot/1.0)"}
        resp = httpx.get(url, headers=headers, follow_redirects=True, timeout=15)
        resp.raise_for_status()
        flags = re.IGNORECASE | re.DOTALL
        match = re.search(r'<meta[^>]+property=["\']og:description["\'][^>]+content=["\'](.*?)["\']', resp.text, flags)
        if match:
            return unescape(match.group(1))
        match = re.search(r'<meta[^>]+content=["\'](.*?)["\'][^>]+property=["\']og:description["\']', resp.text, flags)
        if match:
            return unescape(match.group(1))
    except Exception as e:
        logger.warning(f"Instagram fallback httpx falhou: {e}")
    return ""


class InstagramExtractor:
    """Extrai conteúdo de posts do Instagram com cascata de fallbacks."""

    def __init__(
        self,
        username: str | None = None,
        password: str | None = None,
    ):
        self._loader = instaloader.Instaloader(quiet=True)
        self._whisper_model = None
        self._whisper_model_size = os.getenv("WHISPER_MODEL_SIZE", "base")
        username = username or os.getenv("INSTAGRAM_USERNAME")
        password = password or os.getenv("INSTAGRAM_PASSWORD")
        if username and password:
            try:
                self._loader.login(username, password)
            except Exception as e:
                logger.warning(f"Instagram login falhou: {e}")

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
            # Se instaloader falhou e pode ser vídeo, tenta yt-dlp + Whisper
            try:
                logger.info("Instagram: tentando yt-dlp + Whisper para transcrição de vídeo")
                transcription = self._transcribe_video(url)
                sources["transcricao_audio"] = transcription
            except Exception as e2:
                logger.warning(f"yt-dlp + Whisper falhou: {e2}")

        return {"sources": sources, "images": images}

    def _extract_via_instaloader(self, url: str) -> dict:
        """Extrai conteúdo usando instaloader."""
        shortcode = extract_shortcode(url)
        post = instaloader.Post.from_shortcode(self._loader.context, shortcode)
        caption = post.caption or ""
        sources: dict[str, str] = {}
        images: list[bytes] = []

        if caption:
            sources["caption"] = caption

        if post.is_video:
            logger.info("Instagram: post de vídeo, transcrevendo com yt-dlp + Whisper")
            transcription = self._transcribe_video(url)
            sources["transcricao_audio"] = transcription
        elif len(caption.strip()) < _CAPTION_MIN_LENGTH:
            logger.info("Instagram: caption curta, baixando imagens para visão")
            images = self._download_images(post)

        return {"sources": sources, "images": images}

    def _download_images(self, post) -> list[bytes]:
        """Baixa as imagens do post e retorna como lista de bytes."""
        images = []
        with tempfile.TemporaryDirectory() as tmpdir:
            self._loader.download_post(post, target=Path(tmpdir))
            for img_file in sorted(Path(tmpdir).glob("*.jpg")):
                images.append(img_file.read_bytes())
        return images

    def _transcribe_video(self, url: str) -> str:
        """Baixa o áudio do vídeo com yt-dlp e transcreve com Whisper.

        Execução síncrona intencional: este método é chamado de dentro de uma
        thread (via `asyncio.to_thread` no `InstagramAgent`), portanto não deve
        usar `asyncio.to_thread` internamente.

        O modelo Whisper é carregado em lazy singleton para reutilização entre
        chamadas na mesma sessão.
        """
        import whisper
        import yt_dlp

        if self._whisper_model is None:
            logger.info("Instagram: carregando modelo Whisper")
            self._whisper_model = whisper.load_model(self._whisper_model_size)

        with tempfile.TemporaryDirectory() as tmpdir:
            audio_path = str(Path(tmpdir) / "audio.%(ext)s")
            opts = {
                "format": "bestaudio/best",
                "outtmpl": audio_path,
                "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3"}],
                "quiet": True,
                "no_warnings": True,
            }
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])
            mp3_path = str(Path(tmpdir) / "audio.mp3")
            result = self._whisper_model.transcribe(mp3_path)
            return result["text"]
