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
    )

    result = FacebookPublisher().publish(post)

    if result.status in ("published", "mock_published"):
        print(f"[publish] Facebook {result.status} - post_id={result.external_post_id or 'N/A'}")
        if result.external_url:
            print(f"[publish] URL: {result.external_url}")
    else:
        print(f"[publish] Facebook FAILED: {result.error_message}", file=sys.stderr)
        sys.exit(1)


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

    p = sub.add_parser("publish", help="Post content.json to social platforms")
    p.add_argument("--content-file", default="content.json", help="Content file to publish")
    p.set_defaults(func=cmd_publish)

    ns = parser.parse_args()
    ns.func(ns)


if __name__ == "__main__":
    main()
