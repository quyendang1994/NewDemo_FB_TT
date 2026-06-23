"""Build vertical TikTok video from scenes using FFmpeg."""
from __future__ import annotations
import logging
import uuid
from pathlib import Path
from src import config
from src.models.schemas import TikTokPackage, TikTokScene
from src.services.tts_service import generate_audio
from src.utils.ffmpeg_utils import check_ffmpeg, run_ffmpeg

logger = logging.getLogger(__name__)

WIDTH, HEIGHT = 1080, 1920
BG_COLORS = ["#1a1a2e", "#16213e", "#0f3460", "#e94560"]


def build_video(tiktok: TikTokPackage, job_id: str, language: str = "vi") -> str | None:
    """Build MP4 from TikTok package. Returns output path or None on failure."""
    if not check_ffmpeg():
        logger.error("FFmpeg not available — cannot build video")
        return None

    out_dir = config.OUTPUT_DIR
    audio_dir = out_dir / "audio"
    img_dir = out_dir / "images"
    video_dir = out_dir / "videos"

    full_narration = tiktok.narration_script or " ".join(s.narration for s in tiktok.scenes)
    audio_path = audio_dir / f"{job_id}_narration.mp3"
    audio_ok = generate_audio(full_narration, audio_path, language)

    scene_clips: list[Path] = []
    for scene in tiktok.scenes:
        clip = _build_scene_clip(scene, img_dir, video_dir, job_id, audio_ok)
        if clip:
            scene_clips.append(clip)

    if not scene_clips:
        logger.error("No scene clips generated")
        return None

    output_path = video_dir / f"{job_id}_final.mp4"
    concat_file = video_dir / f"{job_id}_concat.txt"
    with open(concat_file, "w") as f:
        for clip in scene_clips:
            f.write(f"file '{clip.absolute()}'\n")

    args = [
        "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file),
    ]
    if audio_ok and audio_path.exists():
        args += ["-i", str(audio_path), "-c:v", "libx264", "-c:a", "aac",
                 "-shortest", "-pix_fmt", "yuv420p", str(output_path)]
    else:
        args += ["-c:v", "libx264", "-pix_fmt", "yuv420p", str(output_path)]

    ok = run_ffmpeg(args)
    if ok and output_path.exists():
        return str(output_path)
    return None


def _build_scene_clip(scene: TikTokScene, img_dir: Path, video_dir: Path, job_id: str, has_audio: bool) -> Path | None:
    from PIL import Image, ImageDraw, ImageFont
    color = BG_COLORS[scene.scene_number % len(BG_COLORS)]
    img = Image.new("RGB", (WIDTH, HEIGHT), color=color)
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("arial.ttf", 60)
        small_font = ImageFont.truetype("arial.ttf", 40)
    except Exception:
        font = ImageFont.load_default()
        small_font = font

    _draw_wrapped(draw, scene.on_screen_text, font, WIDTH, HEIGHT // 2 - 100, WIDTH - 100)
    img_path = img_dir / f"{job_id}_scene{scene.scene_number}.jpg"
    img.save(str(img_path))

    clip_path = video_dir / f"{job_id}_clip{scene.scene_number}.mp4"
    args = [
        "-y", "-loop", "1", "-i", str(img_path),
        "-t", str(scene.duration_seconds),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "24",
        str(clip_path),
    ]
    ok = run_ffmpeg(args)
    return clip_path if ok else None


def _draw_wrapped(draw: "ImageDraw.ImageDraw", text: str, font, max_width: int, y_start: int, wrap_width: int) -> None:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        test = f"{current} {word}".strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] <= wrap_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)

    y = y_start
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        x = (max_width - bbox[2]) // 2
        draw.text((x, y), line, fill="white", font=font)
        y += bbox[3] + 10
