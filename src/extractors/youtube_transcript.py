# src/extractors/youtube_transcript.py
"""
Extrator de texto para vídeos do YouTube com coleta de múltiplas fontes:

- **Metadata** (título + descrição) — via yt-dlp com `skip_download=True`.
- **Legenda** — YouTube Transcript API, preferência pt → en.
- **Whisper** — fallback: baixa áudio e transcreve localmente. Só acionado
  quando não há legenda NEM descrição útil.

O método `extract_sources()` coleta TODAS as fontes disponíveis e retorna
um `dict[str, str]`. O método legado `extract_text()` delega para
`extract_sources()` e concatena os valores.
"""
import asyncio
import logging
import os
import re
import tempfile
from pathlib import Path

from youtube_transcript_api import YouTubeTranscriptApi

logger = logging.getLogger(__name__)


def extract_video_id(url: str) -> str:
    """Extrai o ID do vídeo de URLs do YouTube (watch, youtu.be, shorts)."""
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

    async def extract_sources(self, url: str) -> dict[str, str]:
        """Coleta todas as fontes disponíveis para o vídeo."""
        video_id = extract_video_id(url)
        sources: dict[str, str] = {}

        # Metadata (título + descrição) via yt-dlp
        try:
            title, description = await asyncio.to_thread(self._get_metadata, url)
            if title:
                sources["titulo"] = title
            if description and len(description.strip()) > 100:
                sources["descricao"] = description
        except Exception as e:
            logger.warning(f"YouTube metadata falhou: {e}")

        # Legenda via Transcript API
        try:
            api = YouTubeTranscriptApi()
            transcript = await asyncio.to_thread(
                api.fetch, video_id, languages=["pt", "en"]
            )
            sources["legenda"] = " ".join(snippet.text for snippet in transcript)
            logger.info("YouTube: legenda extraída via API")
        except Exception as e:
            logger.warning(f"YouTube transcript API falhou: {e}")

        # Whisper: último recurso, só se não tem legenda NEM descrição
        if "legenda" not in sources and "descricao" not in sources:
            logger.info("YouTube: fallback para Whisper")
            sources["transcricao_whisper"] = await self._whisper_transcribe(url)

        return sources

    async def extract_text(self, url: str) -> str:
        """Wrapper legado: coleta fontes e retorna como texto único."""
        sources = await self.extract_sources(url)
        return "\n\n".join(sources.values())

    def _get_metadata(self, url: str) -> tuple[str, str]:
        """Obtém título e descrição do vídeo via yt-dlp sem download."""
        import yt_dlp

        opts = {"quiet": True, "no_warnings": True, "skip_download": True}
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return info.get("title", ""), info.get("description", "")

    async def _whisper_transcribe(self, url: str) -> str:
        """Baixa o áudio e transcreve com Whisper."""
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
