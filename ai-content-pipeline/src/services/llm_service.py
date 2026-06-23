"""LLM adapter — Anthropic Claude with mock fallback."""
from __future__ import annotations
import json
import logging
from src import config

logger = logging.getLogger(__name__)

_MOCK_RESEARCH = {
    "title": "Tổng hợp thông tin về chủ đề",
    "short_summary": "Đây là bản tóm tắt mẫu được tạo ở mock mode vì chưa có ANTHROPIC_API_KEY.",
    "key_points": [
        "Điểm chính thứ nhất từ nguồn [S1].",
        "Điểm chính thứ hai từ nguồn [S2].",
        "Điểm chính thứ ba từ các nguồn khác.",
    ],
    "detailed_summary": "Đây là bản tóm tắt chi tiết mẫu. Nội dung thực sẽ được tổng hợp từ các nguồn [S1], [S2], [S3] khi cấu hình API key.",
    "source_ids_used": ["S1", "S2", "S3"],
    "uncertainties": ["Cần ANTHROPIC_API_KEY để tạo nội dung thật."],
    "safety_notes": [],
}

_MOCK_SOCIAL = {
    "facebook": {
        "title": "Tiêu đề bài viết Facebook mẫu",
        "body": "Đây là nội dung bài viết Facebook mẫu. Thêm ANTHROPIC_API_KEY để tạo nội dung thật từ nghiên cứu web.",
        "hashtags": ["#AI", "#TechNews", "#Vietnam"],
        "source_references": ["[S1] https://example.com/source1", "[S2] https://example.com/source2"],
    },
    "tiktok": {
        "hook": "Bạn có biết AI đang thay đổi thế giới không?",
        "narration_script": "Đây là kịch bản TikTok mẫu. Cần ANTHROPIC_API_KEY để tạo nội dung thật.",
        "caption": "Caption TikTok mẫu 🤖",
        "hashtags": ["#AI", "#TikTok", "#LearnWithTikTok"],
        "scenes": [
            {"scene_number": 1, "duration_seconds": 3, "narration": "Hook mở đầu hấp dẫn.", "on_screen_text": "Tiêu đề"},
            {"scene_number": 2, "duration_seconds": 10, "narration": "Nội dung chính.", "on_screen_text": "Điểm 1"},
            {"scene_number": 3, "duration_seconds": 5, "narration": "Kết thúc kêu gọi.", "on_screen_text": "Kết luận"},
        ],
        "call_to_action": "Follow để biết thêm!",
    },
}


def call_llm(system_prompt: str, user_message: str, max_retries: int = 2) -> dict:
    """Call Anthropic Claude and return parsed JSON. Falls back to mock if no key."""
    if not config.ANTHROPIC_API_KEY:
        logger.warning("ANTHROPIC_API_KEY not set — returning mock LLM response")
        if "social" in system_prompt.lower() or "facebook" in system_prompt.lower():
            return _MOCK_SOCIAL
        return _MOCK_RESEARCH

    import anthropic
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

    for attempt in range(1, max_retries + 2):
        try:
            message = client.messages.create(
                model=config.ANTHROPIC_MODEL,
                max_tokens=4096,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
            )
            raw = message.content[0].text.strip()
            # Strip markdown code fences if present
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            logger.warning("LLM returned invalid JSON on attempt %d: %s", attempt, exc)
            if attempt > max_retries:
                raise RuntimeError("LLM returned invalid JSON after retries") from exc
        except Exception as exc:
            logger.error("LLM call failed: %s", exc)
            raise
    return {}
