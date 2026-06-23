"""FFmpeg wrapper utilities."""
from __future__ import annotations
import logging
import shutil
import subprocess

logger = logging.getLogger(__name__)


def check_ffmpeg() -> bool:
    """Return True if ffmpeg is available on PATH."""
    return shutil.which("ffmpeg") is not None


def run_ffmpeg(args: list[str], timeout: int = 120) -> bool:
    """Run ffmpeg with given args. Returns True on success."""
    cmd = ["ffmpeg"] + args
    logger.debug("Running: %s", " ".join(cmd))
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if result.returncode != 0:
            logger.error("FFmpeg error: %s", result.stderr[-500:])
            return False
        return True
    except subprocess.TimeoutExpired:
        logger.error("FFmpeg timed out after %ds", timeout)
        return False
    except Exception as exc:
        logger.error("FFmpeg exception: %s", exc)
        return False
