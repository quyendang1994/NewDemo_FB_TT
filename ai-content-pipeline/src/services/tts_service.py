"""Generate voice-over audio using edge-tts."""
from __future__ import annotations
import asyncio
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

VOICE_VI = "vi-VN-NamMinhNeural"
VOICE_EN = "en-US-AriaNeural"


def generate_audio(text: str, output_path: Path, language: str = "vi") -> bool:
    """Generate TTS audio file. Returns True on success."""
    try:
        import edge_tts
    except ImportError:
        logger.error("edge-tts not installed")
        return False

    voice = VOICE_VI if language == "vi" else VOICE_EN
    try:
        asyncio.run(_tts(text, voice, str(output_path)))
        logger.info("Audio generated: %s", output_path)
        return True
    except Exception as exc:
        logger.error("TTS failed: %s", exc)
        return False


async def _tts(text: str, voice: str, path: str) -> None:
    import edge_tts
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(path)
