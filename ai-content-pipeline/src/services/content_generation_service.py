"""Generate Facebook and TikTok content from research results."""
from __future__ import annotations
import logging
from src.models.schemas import ResearchResult, SourceItem, SocialContent, FacebookPost, TikTokPackage, TikTokScene
from src.services import llm_service
from src.prompts import load_prompt

logger = logging.getLogger(__name__)


def generate_social_content(
    research: ResearchResult,
    sources: list[SourceItem],
    language: str = "vi",
    generate_facebook: bool = True,
    generate_tiktok: bool = True,
) -> SocialContent:
    """Generate Facebook and TikTok drafts from research results."""
    system_prompt = load_prompt("content_generation_prompt.txt")

    source_refs = "\n".join(f"[{s.source_id}] {s.title} — {s.url}" for s in sources)
    user_message = (
        f"Ngôn ngữ: {language}\n"
        f"Tạo Facebook: {generate_facebook}\nTạo TikTok: {generate_tiktok}\n\n"
        f"=== RESEARCH ===\n"
        f"Tiêu đề: {research.title}\n"
        f"Tóm tắt: {research.detailed_summary}\n"
        f"Điểm chính: {chr(10).join(research.key_points)}\n\n"
        f"=== NGUỒN ===\n{source_refs}"
    )

    raw = llm_service.call_llm(system_prompt, user_message)

    fb_data = raw.get("facebook", {})
    tk_data = raw.get("tiktok", {})

    facebook = FacebookPost(
        title=fb_data.get("title", research.title),
        body=fb_data.get("body", ""),
        hashtags=fb_data.get("hashtags", []),
        source_references=fb_data.get("source_references", []),
    )

    scenes = [TikTokScene(**sc) for sc in tk_data.get("scenes", [])]
    tiktok = TikTokPackage(
        hook=tk_data.get("hook", ""),
        narration_script=tk_data.get("narration_script", ""),
        caption=tk_data.get("caption", ""),
        hashtags=tk_data.get("hashtags", []),
        scenes=scenes,
        call_to_action=tk_data.get("call_to_action", ""),
    )

    return SocialContent(facebook=facebook, tiktok=tiktok)
