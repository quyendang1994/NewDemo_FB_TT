"""Tests for LLM JSON parsing logic."""
import pytest
from unittest.mock import patch, MagicMock
from src.models.schemas import ResearchResult, SocialContent, FacebookPost, TikTokPackage, TikTokScene


def test_research_result_from_valid_json():
    data = {
        "user_prompt": "AI 2025",
        "title": "T",
        "short_summary": "S",
        "key_points": ["kp"],
        "detailed_summary": "D [S1]",
        "source_ids_used": ["S1"],
        "uncertainties": [],
        "safety_notes": [],
    }
    r = ResearchResult(**data)
    assert r.title == "T"
    assert r.source_ids_used == ["S1"]


def test_research_result_missing_field():
    with pytest.raises(Exception):
        ResearchResult(title="T")  # type: ignore[call-arg]


def test_llm_service_mock_mode_research():
    """When ANTHROPIC_API_KEY is absent, returns mock research data."""
    import importlib
    import src.services.llm_service as llm_module
    original = llm_module.config.ANTHROPIC_API_KEY
    try:
        llm_module.config.ANTHROPIC_API_KEY = None  # type: ignore[assignment]
        result = llm_module.call_llm("research system prompt", "some query")
        assert "title" in result
    finally:
        llm_module.config.ANTHROPIC_API_KEY = original  # type: ignore[assignment]


def test_llm_service_mock_mode_social():
    """When ANTHROPIC_API_KEY is absent, returns mock social data for social prompt."""
    import src.services.llm_service as llm_module
    original = llm_module.config.ANTHROPIC_API_KEY
    try:
        llm_module.config.ANTHROPIC_API_KEY = None  # type: ignore[assignment]
        result = llm_module.call_llm("generate facebook and social content", "query")
        assert "facebook" in result
    finally:
        llm_module.config.ANTHROPIC_API_KEY = original  # type: ignore[assignment]


def test_social_content_from_dict():
    data = {
        "facebook": {
            "title": "FB Title",
            "body": "Body text",
            "hashtags": ["#AI"],
            "source_references": ["[S1] https://example.com"],
        },
        "tiktok": {
            "hook": "Hook!",
            "narration_script": "Script",
            "caption": "Caption",
            "hashtags": ["#TikTok"],
            "scenes": [
                {"scene_number": 1, "duration_seconds": 4, "narration": "n", "on_screen_text": "t"}
            ],
            "call_to_action": "Follow!",
        },
    }
    fb = FacebookPost(**data["facebook"])
    scenes = [TikTokScene(**s) for s in data["tiktok"]["scenes"]]
    tk_data = {**data["tiktok"], "scenes": scenes}
    tk = TikTokPackage(**tk_data)
    assert fb.title == "FB Title"
    assert tk.hook == "Hook!"
    assert len(tk.scenes) == 1
