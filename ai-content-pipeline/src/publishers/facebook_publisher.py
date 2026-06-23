"""Facebook Graph API publisher with mock fallback."""
from __future__ import annotations
import logging
from datetime import datetime, timezone
import httpx
from src import config
from src.models.schemas import FacebookPost, PublishResult
from src.publishers.base import BasePublisher

logger = logging.getLogger(__name__)
GRAPH_API = "https://graph.facebook.com/v19.0"


class FacebookPublisher(BasePublisher):
    @property
    def is_configured(self) -> bool:
        return bool(config.FACEBOOK_PAGE_ID and config.FACEBOOK_PAGE_ACCESS_TOKEN and config.ENABLE_REAL_PUBLISHING)

    def publish(self, post: FacebookPost) -> PublishResult:  # type: ignore[override]
        now = datetime.now(timezone.utc)
        if not self.is_configured:
            logger.info("Mock publish Facebook: %s", post.title[:50])
            return PublishResult(platform="facebook", status="mock_published", published_at=now)

        text = f"{post.title}\n\n{post.body}\n\n{chr(10).join(post.hashtags)}"
        url = f"{GRAPH_API}/{config.FACEBOOK_PAGE_ID}/feed"
        try:
            resp = httpx.post(url, data={"message": text, "access_token": config.FACEBOOK_PAGE_ACCESS_TOKEN}, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            post_id = data.get("id")
            logger.info("Facebook published: %s", post_id)
            return PublishResult(
                platform="facebook", status="published",
                external_post_id=post_id,
                external_url=f"https://www.facebook.com/{post_id}",
                published_at=now,
            )
        except Exception as exc:
            logger.error("Facebook publish failed: %s", type(exc).__name__)
            return PublishResult(platform="facebook", status="failed", error_message=str(exc)[:200], published_at=now)
