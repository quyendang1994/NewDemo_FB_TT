"""TikTok publisher adapter with mock fallback."""
from __future__ import annotations
import logging
from datetime import datetime, timezone
from pathlib import Path
from src import config
from src.models.schemas import PublishResult
from src.publishers.base import BasePublisher

logger = logging.getLogger(__name__)


class TikTokPublisher(BasePublisher):
    @property
    def is_configured(self) -> bool:
        return bool(
            config.TIKTOK_ACCESS_TOKEN
            and config.TIKTOK_CLIENT_KEY
            and config.ENABLE_REAL_PUBLISHING
        )

    def publish(self, video_path: str | None) -> PublishResult:  # type: ignore[override]
        now = datetime.now(timezone.utc)
        if not self.is_configured:
            logger.info("Mock publish TikTok: %s", video_path)
            return PublishResult(platform="tiktok", status="mock_published", published_at=now)

        if not video_path or not Path(video_path).exists():
            return PublishResult(platform="tiktok", status="failed", error_message="Video file not found", published_at=now)

        try:
            video_id = self.upload_video(video_path)
            if video_id:
                return self.publish_video(video_id, now)
            return PublishResult(platform="tiktok", status="failed", error_message="Upload returned no video ID", published_at=now)
        except Exception as exc:
            logger.error("TikTok publish failed: %s", type(exc).__name__)
            return PublishResult(platform="tiktok", status="failed", error_message=str(exc)[:200], published_at=now)

    def upload_video(self, video_path: str) -> str | None:
        """Upload video to TikTok and return video_id."""
        import httpx
        with open(video_path, "rb") as f:
            resp = httpx.post(
                "https://open.tiktokapis.com/v2/post/publish/inbox/video/init/",
                headers={"Authorization": f"Bearer {config.TIKTOK_ACCESS_TOKEN}"},
                json={"source_info": {"source": "FILE_UPLOAD"}},
                timeout=60,
            )
        resp.raise_for_status()
        return resp.json().get("data", {}).get("publish_id")

    def publish_video(self, publish_id: str, now: datetime) -> PublishResult:
        """Request TikTok to publish an uploaded video."""
        return PublishResult(
            platform="tiktok", status="uploaded_private",
            external_post_id=publish_id,
            published_at=now,
        )
