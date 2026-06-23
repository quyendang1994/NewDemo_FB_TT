"""Tests for Pydantic schema validation."""
import pytest
from datetime import datetime, timezone
from pydantic import ValidationError
from src.models.schemas import (
    SourceItem,
    ResearchResult,
    TikTokScene,
    TikTokPackage,
    FacebookPost,
    SocialContent,
)


def make_source(source_id: str = "S1", url: str = "https://example.com/article") -> SourceItem:
    return SourceItem(
        source_id=source_id,
        title="Test Article",
        url=url,  # type: ignore[arg-type]
        domain="example.com",
        retrieved_at=datetime.now(timezone.utc),
        extracted_content="Test content",
        extraction_status="success",
    )


def test_source_item_valid():
    s = make_source()
    assert s.source_id == "S1"
    assert s.domain == "example.com"
    assert s.extraction_status == "success"


def test_source_item_invalid_status():
    with pytest.raises(ValidationError):
        SourceItem(
            source_id="S1",
            title="T",
            url="https://example.com",  # type: ignore[arg-type]
            domain="example.com",
            retrieved_at=datetime.now(timezone.utc),
            extracted_content="",
            extraction_status="unknown",  # type: ignore[arg-type]
        )


def test_source_item_invalid_url():
    with pytest.raises(ValidationError):
        SourceItem(
            source_id="S1",
            title="T",
            url="not-a-url",  # type: ignore[arg-type]
            domain="x",
            retrieved_at=datetime.now(timezone.utc),
            extracted_content="",
            extraction_status="failed",
        )


def test_research_result_valid():
    r = ResearchResult(
        user_prompt="test",
        title="T",
        short_summary="S",
        key_points=["kp1"],
        detailed_summary="D",
        source_ids_used=["S1"],
        uncertainties=[],
        safety_notes=[],
    )
    assert r.title == "T"
    assert r.source_ids_used == ["S1"]


def test_tiktok_scene_duration():
    scene = TikTokScene(scene_number=1, duration_seconds=5, narration="hello", on_screen_text="Hi")
    assert scene.duration_seconds == 5


def test_tiktok_scene_zero_duration():
    scene = TikTokScene(scene_number=1, duration_seconds=0, narration="x", on_screen_text="y")
    assert scene.duration_seconds == 0


def test_social_content_nested():
    fb = FacebookPost(title="T", body="B", hashtags=["#AI"], source_references=["[S1] url"])
    tk = TikTokPackage(
        hook="H",
        narration_script="N",
        caption="C",
        hashtags=["#AI"],
        scenes=[TikTokScene(scene_number=1, duration_seconds=3, narration="n", on_screen_text="t")],
        call_to_action="CTA",
    )
    sc = SocialContent(facebook=fb, tiktok=tk)
    assert sc.facebook.title == "T"
    assert len(sc.tiktok.scenes) == 1
