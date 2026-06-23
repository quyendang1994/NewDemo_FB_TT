"""Pydantic v2 schemas for data flowing between pipeline layers."""
from __future__ import annotations
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, HttpUrl


class SourceItem(BaseModel):
    source_id: str
    title: str
    url: HttpUrl
    domain: str
    snippet: str | None = None
    published_date: datetime | None = None
    retrieved_at: datetime
    extracted_content: str
    extraction_status: Literal["success", "partial", "failed"]


class ResearchResult(BaseModel):
    user_prompt: str
    title: str
    short_summary: str
    key_points: list[str]
    detailed_summary: str
    source_ids_used: list[str]
    uncertainties: list[str]
    safety_notes: list[str]


class FacebookPost(BaseModel):
    title: str
    body: str
    hashtags: list[str]
    source_references: list[str]


class TikTokScene(BaseModel):
    scene_number: int
    duration_seconds: int
    narration: str
    on_screen_text: str


class TikTokPackage(BaseModel):
    hook: str
    narration_script: str
    caption: str
    hashtags: list[str]
    scenes: list[TikTokScene]
    call_to_action: str


class SocialContent(BaseModel):
    facebook: FacebookPost
    tiktok: TikTokPackage


class PublishResult(BaseModel):
    platform: Literal["facebook", "tiktok"]
    status: Literal["mock_published", "published", "uploaded_private", "failed"]
    external_post_id: str | None = None
    external_url: str | None = None
    error_message: str | None = None
    published_at: datetime


class PipelineJob(BaseModel):
    job_id: str
    prompt: str
    language: str
    max_sources: int
    generate_facebook: bool
    generate_tiktok: bool
    created_at: datetime
    status: Literal["running", "done", "failed"]
    sources: list[SourceItem] = []
    research: ResearchResult | None = None
    content: SocialContent | None = None
    video_path: str | None = None
    publish_results: list[PublishResult] = []
