#!/usr/bin/env python3
"""CLI for AI Content Pipeline in Claude Code agent mode.

Separates I/O (search, extract, publish) from LLM so Claude Code
handles synthesis and content generation natively.

Commands:
  gather   -- search web + extract content -> sources.json (no LLM calls)
  publish  -- read content.json and post to Facebook/TikTok
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

# Ensure src/ is importable and .env is found regardless of CWD
_PIPELINE_DIR = Path(__file__).resolve().parent
if str(_PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(_PIPELINE_DIR))

from dotenv import load_dotenv  # noqa: E402
load_dotenv(_PIPELINE_DIR / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)


def cmd_gather(args: argparse.Namespace) -> None:
    """Search + extract sources, output JSON. No Anthropic API calls."""
    from src.services import search_service, content_extractor, source_deduplicator
    from src import config

    max_s = args.max_sources
    logger.info("Searching: %s", args.topic)

    raw = search_service.search_web(args.topic, max_results=max_s + 3)
    sources = search_service.build_source_items(raw)
    sources = source_deduplicator.deduplicate_sources(sources)
    sources = sources[: max_s + 2]

    extracted = []
    for s in sources:
        updated = content_extractor.extract_content(s)
        extracted.append(updated)
        logger.info("[%s] %s -> %s", updated.source_id, updated.domain, updated.extraction_status)

    good = source_deduplicator.filter_poor_sources(extracted) or extracted[:3]
    final = [
        s.model_copy(update={"source_id": f"S{i}"})
        for i, s in enumerate(good[:max_s], start=1)
    ]

    output = {
        "topic": args.topic,
        "language": args.language,
        "sources": [
            {
                "source_id": s.source_id,
                "title": s.title,
                "url": str(s.url),
                "domain": s.domain,
                "content": s.extracted_content[: config.MAX_EXTRACTED_CHARS_PER_SOURCE],
                "extraction_status": s.extraction_status,
            }
            for s in final
        ],
    }

    payload = json.dumps(output, ensure_ascii=False, indent=2)
    out_path = Path(args.output)
    out_path.write_text(payload, encoding="utf-8")
    print(f"[gather] {len(final)} sources saved -> {out_path}")


def _draw_wrapped_text(draw, text: str, font, canvas_w: int, y_start: int, max_w: int) -> None:
    """Draw word-wrapped text centered horizontally."""
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        test = f"{current} {word}".strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] <= max_w:
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
        x = (canvas_w - bbox[2]) // 2
        draw.text((x, y), line, fill="white", font=font)
        y += bbox[3] + 14


def cmd_synthesize(args: argparse.Namespace) -> None:
    """Call Anthropic SDK to synthesize sources.json -> content.json."""
    import os
    import re

    try:
        import anthropic
    except ImportError:
        print("ERROR: anthropic package not installed — run: pip install anthropic", file=sys.stderr)
        sys.exit(1)

    sources_path = Path(args.sources_file)
    if not sources_path.exists():
        print(f"ERROR: File not found: {sources_path}", file=sys.stderr)
        sys.exit(1)

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set in .env", file=sys.stderr)
        sys.exit(1)

    data = json.loads(sources_path.read_text(encoding="utf-8"))
    topic = data.get("topic", "")
    language = data.get("language", args.language)
    sources = data.get("sources", [])
    lang_name = "Vietnamese" if language == "vi" else "English"

    sources_text = ""
    for s in sources:
        sources_text += (
            f"\n---\n[{s['source_id']}] {s['title']}\n"
            f"URL: {s['url']}\n"
            f"{s.get('content', '')[:2000]}\n"
        )

    prompt = (
        f"You are a professional social media content creator writing in {lang_name}.\n"
        f"Topic: {topic}\n\n"
        f"Research sources:\n{sources_text}\n\n"
        "Based on the research above, generate a JSON object with EXACTLY this structure.\n"
        "Output ONLY valid JSON — no markdown fences, no explanation, nothing else.\n\n"
        "{\n"
        '  "facebook": {\n'
        '    "title": "engaging post title",\n'
        '    "body": "post body 300-500 words",\n'
        '    "hashtags": ["#tag1", "#tag2", "#tag3", "#tag4", "#tag5"],\n'
        '    "source_references": ["domain1.com", "domain2.com"]\n'
        "  },\n"
        '  "tiktok": {\n'
        '    "hook": "hook under 10 words",\n'
        '    "narration_script": "full 60-90s narration",\n'
        '    "caption": "caption under 150 chars",\n'
        '    "hashtags": ["#tag1", "#tag2", "#tag3"],\n'
        '    "call_to_action": "CTA text",\n'
        '    "scenes": [\n'
        '      {"scene_number": 1, "duration_seconds": 5, "narration": "...", "on_screen_text": "..."},\n'
        '      {"scene_number": 2, "duration_seconds": 8, "narration": "...", "on_screen_text": "..."},\n'
        '      {"scene_number": 3, "duration_seconds": 8, "narration": "...", "on_screen_text": "..."},\n'
        '      {"scene_number": 4, "duration_seconds": 7, "narration": "...", "on_screen_text": "..."},\n'
        '      {"scene_number": 5, "duration_seconds": 7, "narration": "...", "on_screen_text": "..."}\n'
        "    ]\n"
        "  },\n"
        f'  "language": "{language}",\n'
        f'  "topic": "{topic}"\n'
        "}"
    )

    from src import config
    model = getattr(config, "ANTHROPIC_MODEL", None) or "claude-sonnet-4-6"
    print(f"[synthesize] Calling Anthropic SDK (model={model}) ...")

    try:
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model=model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        output = message.content[0].text.strip()
    except anthropic.APIError as exc:
        print(f"ERROR: Anthropic API error: {exc}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"ERROR: Failed to call Anthropic SDK: {exc}", file=sys.stderr)
        sys.exit(1)

    def _extract_json(text: str) -> dict | None:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        m = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text)
        if m:
            try:
                return json.loads(m.group(1))
            except json.JSONDecodeError:
                pass
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                pass
        return None

    content = _extract_json(output)
    if content is None:
        print("ERROR: No valid JSON found in API response", file=sys.stderr)
        print("--- raw output (first 1000 chars) ---", file=sys.stderr)
        print(output[:1000], file=sys.stderr)
        sys.exit(1)

    out_path = Path(args.output)
    out_path.write_text(json.dumps(content, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[synthesize] content.json saved -> {out_path}")


def cmd_build_image(args: argparse.Namespace) -> None:
    """Build Facebook card image (1200x628) from content.json using Pillow."""
    import hashlib
    import uuid

    path = Path(args.content_file)
    if not path.exists():
        print(f"ERROR: File not found: {path}", file=sys.stderr)
        sys.exit(1)

    data = json.loads(path.read_text(encoding="utf-8"))
    fb = data.get("facebook", {})
    if not fb:
        print("ERROR: No 'facebook' field in content.json", file=sys.stderr)
        sys.exit(1)

    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("ERROR: Pillow not installed — run: pip install Pillow", file=sys.stderr)
        sys.exit(1)

    from src import config

    title = fb.get("title", "Bài viết")
    hashtags = "  ".join(fb.get("hashtags", [])[:5])

    W, H = 1200, 628
    BG_COLORS = ["#1a1a2e", "#0f3460", "#16213e", "#2c3e50", "#1b2838"]
    ACCENT_COLORS = ["#e94560", "#f5a623", "#3b82f6", "#22c55e", "#a855f7"]
    idx = int(hashlib.md5(title.encode()).hexdigest(), 16) % len(BG_COLORS)
    bg = BG_COLORS[idx]
    accent = ACCENT_COLORS[idx]

    img = Image.new("RGB", (W, H), color=bg)
    draw = ImageDraw.Draw(img)

    # Left accent bar
    draw.rectangle([0, 0, 10, H], fill=accent)
    # Bottom accent bar
    draw.rectangle([0, H - 10, W, H], fill=accent)

    try:
        title_font = ImageFont.truetype("arial.ttf", 56)
        tag_font = ImageFont.truetype("arial.ttf", 32)
    except Exception:
        title_font = ImageFont.load_default()
        tag_font = title_font

    _draw_wrapped_text(draw, title, title_font, W, H // 2 - 80, W - 160)

    if hashtags:
        bbox = draw.textbbox((0, 0), hashtags, font=tag_font)
        x = (W - bbox[2]) // 2
        draw.text((x, H - 80), hashtags, fill=accent, font=tag_font)

    out_dir = config.OUTPUT_DIR / "images"
    out_dir.mkdir(parents=True, exist_ok=True)
    job_id = args.job_id or f"fb_{uuid.uuid4().hex[:8]}"
    out_path = out_dir / f"{job_id}_card.jpg"
    img.save(str(out_path), quality=95)

    print(f"[build-image] Image saved: {out_path}")
    data["image_path"] = str(out_path)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def cmd_build_video(args: argparse.Namespace) -> None:
    """Build TikTok video from content.json (requires FFmpeg + Pillow)."""
    import uuid
    from src.models.schemas import TikTokPackage
    from src.services.video_builder import build_video

    path = Path(args.content_file)
    if not path.exists():
        print(f"ERROR: File not found: {path}", file=sys.stderr)
        sys.exit(1)

    data = json.loads(path.read_text(encoding="utf-8"))
    tk = data.get("tiktok", {})
    if not tk:
        print("ERROR: No 'tiktok' field in content.json", file=sys.stderr)
        sys.exit(1)

    package = TikTokPackage.model_validate(tk)
    language = data.get("language", args.language)
    job_id = args.job_id or f"job_{uuid.uuid4().hex[:8]}"

    logger.info("Building TikTok video for job: %s", job_id)
    result = build_video(package, job_id, language)

    if result:
        print(f"[build-video] Video saved: {result}")
        data["video_path"] = result
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        print("ERROR: Video build failed — check FFmpeg and Pillow installation", file=sys.stderr)
        sys.exit(1)


def cmd_publish(args: argparse.Namespace) -> None:
    """Read content.json and publish to Facebook."""
    from src.models.schemas import FacebookPost
    from src.publishers.facebook_publisher import FacebookPublisher

    path = Path(args.content_file)
    if not path.exists():
        print(f"ERROR: File not found: {path}", file=sys.stderr)
        sys.exit(1)

    data = json.loads(path.read_text(encoding="utf-8"))
    fb = data.get("facebook", {})

    post = FacebookPost(
        title=fb.get("title", ""),
        body=fb.get("body", ""),
        hashtags=fb.get("hashtags", []),
        source_references=fb.get("source_references", []),
        image_path=data.get("image_path"),
    )

    result = FacebookPublisher().publish(post)

    if result.status in ("published", "mock_published"):
        print(f"[publish] Facebook {result.status} - post_id={result.external_post_id or 'N/A'}")
        if result.external_url:
            print(f"[publish] URL: {result.external_url}")
    else:
        print(f"[publish] Facebook FAILED: {result.error_message}", file=sys.stderr)
        sys.exit(1)


def cmd_run(args: argparse.Namespace) -> None:
    """Run the full pipeline end-to-end: gather → synthesize → build-image → build-video → publish."""
    import uuid
    job_id = f"job_{uuid.uuid4().hex[:8]}"

    print(f"\n{'='*60}")
    print(f"  AI Content Pipeline — chủ đề: {args.topic}")
    print(f"  job_id: {job_id}")
    print(f"{'='*60}\n")

    # Step 1: gather
    print("[1/5] Thu thập nguồn từ web...")
    gather_args = argparse.Namespace(
        topic=args.topic,
        language=args.language,
        max_sources=args.max_sources,
        output=args.sources_file,
    )
    cmd_gather(gather_args)

    # Step 2: synthesize
    print("\n[2/5] Tổng hợp và tạo nội dung (Claude Code)...")
    synth_args = argparse.Namespace(
        sources_file=args.sources_file,
        output=args.content_file,
        language=args.language,
    )
    cmd_synthesize(synth_args)

    # Step 3: build-image
    print("\n[3/5] Tạo ảnh card Facebook...")
    image_args = argparse.Namespace(
        content_file=args.content_file,
        job_id=job_id,
    )
    try:
        cmd_build_image(image_args)
    except SystemExit:
        print("[3/5] Bỏ qua — lỗi tạo ảnh (xem log ở trên)")

    # Step 4: build-video
    print("\n[4/5] Tạo video TikTok...")
    video_args = argparse.Namespace(
        content_file=args.content_file,
        language=args.language,
        job_id=job_id,
    )
    try:
        cmd_build_video(video_args)
    except SystemExit:
        print("[4/5] Bỏ qua — FFmpeg chưa cài hoặc lỗi tạo video")

    # Step 5: publish
    print("\n[5/5] Đăng lên Facebook...")
    pub_args = argparse.Namespace(content_file=args.content_file)
    cmd_publish(pub_args)

    print(f"\n{'='*60}")
    print("  Hoàn thành!")
    print(f"{'='*60}\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="AI Content Pipeline CLI (Claude Code agent mode)"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    g = sub.add_parser("gather", help="Search + extract sources (no LLM)")
    g.add_argument("--topic", required=True, help="Research topic")
    g.add_argument("--language", default="vi", help="Output language (default: vi)")
    g.add_argument("--max-sources", type=int, default=5, help="Max number of sources")
    g.add_argument("--output", default="sources.json", help="Output file (default: sources.json)")
    g.set_defaults(func=cmd_gather)

    sy = sub.add_parser("synthesize", help="Call Claude Code CLI to synthesize sources.json -> content.json")
    sy.add_argument("--sources-file", default="sources.json", help="Input sources file (default: sources.json)")
    sy.add_argument("--output", default="content.json", help="Output content file (default: content.json)")
    sy.add_argument("--language", default="vi", help="Language (default: vi)")
    sy.set_defaults(func=cmd_synthesize)

    bi = sub.add_parser("build-image", help="Build Facebook card image 1200x628 from content.json (needs Pillow)")
    bi.add_argument("--content-file", default="content.json", help="Content file (default: content.json)")
    bi.add_argument("--job-id", default="", help="Job ID prefix for output file name")
    bi.set_defaults(func=cmd_build_image)

    bv = sub.add_parser("build-video", help="Build TikTok MP4 from content.json (needs FFmpeg)")
    bv.add_argument("--content-file", default="content.json", help="Content file (default: content.json)")
    bv.add_argument("--language", default="vi", help="Language for TTS (default: vi)")
    bv.add_argument("--job-id", default="", help="Job ID prefix for output files")
    bv.set_defaults(func=cmd_build_video)

    p = sub.add_parser("publish", help="Post content.json to social platforms")
    p.add_argument("--content-file", default="content.json", help="Content file to publish")
    p.set_defaults(func=cmd_publish)

    r = sub.add_parser("run", help="Run full pipeline: gather -> synthesize -> build-image -> build-video -> publish")
    r.add_argument("--topic", required=True, help="Research topic")
    r.add_argument("--language", default="vi", help="Output language: vi or en (default: vi)")
    r.add_argument("--max-sources", type=int, default=5, help="Max number of sources (default: 5)")
    r.add_argument("--sources-file", default="sources.json", help="Temp sources file (default: sources.json)")
    r.add_argument("--content-file", default="content.json", help="Temp content file (default: content.json)")
    r.set_defaults(func=cmd_run)

    ns = parser.parse_args()
    ns.func(ns)


if __name__ == "__main__":
    main()
