# src/extractors/youtube_transcript.py
import asyncio
import logging
import os
import re
import tempfile
from pathlib import Path

from youtube_transcript_api import YouTubeTranscriptApi

logger = logging.getLogger(__name__)


def extract_video_id(url: str) -> str:
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

    async def extract_text(self, url: str) -> str:
        video_id = extract_video_id(url)

        # Strategy 1: Transcript API
        try:
            api = YouTubeTranscriptApi()
            transcript = await asyncio.to_thread(
                api.fetch, video_id, languages=["pt", "en"]
            )
            text = " ".join(snippet.text for snippet in transcript)
            logger.info("YouTube: extraído via API de legendas")
            return text
        except Exception as e:
            logger.warning(f"YouTube transcript API falhou: {e}")

        # Strategy 2: Video description
        try:
            desc = await asyncio.to_thread(self._get_description, url)
            if desc and len(desc.strip()) > 100:
                logger.info("YouTube: extraído via descrição do vídeo")
                return desc
        except Exception as e:
            logger.warning(f"YouTube descrição falhou: {e}")

        # Strategy 3: Whisper
        logger.info("YouTube: fallback para transcrição Whisper")
        return await self._whisper_transcribe(url)

    def _get_description(self, url: str) -> str:
        import yt_dlp

        opts = {"quiet": True, "no_warnings": True, "skip_download": True}
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return info.get("description", "")

    async def _whisper_transcribe(self, url: str) -> str:
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
