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
        token = config.FACEBOOK_PAGE_ACCESS_TOKEN
        page_id = config.FACEBOOK_PAGE_ID

        # Photo post if image_path provided
        if post.image_path:
            from pathlib import Path as _Path
            img_file = _Path(post.image_path)
            if img_file.exists():
                return self._publish_photo(img_file, text, page_id, token, now)
            else:
                logger.warning("image_path not found, falling back to text post: %s", post.image_path)

        return self._publish_text(text, page_id, token, now)

    def _publish_text(self, text: str, page_id: str, token: str, now) -> PublishResult:
        url = f"{GRAPH_API}/{page_id}/feed"
        try:
            resp = httpx.post(url, data={"message": text, "access_token": token}, timeout=30)
            if not resp.is_success:
                fb_error = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else resp.text
                logger.error("Facebook API error %d: %s", resp.status_code, fb_error)
                return PublishResult(platform="facebook", status="failed", error_message=str(fb_error)[:500], published_at=now)
            post_id = resp.json().get("id")
            logger.info("Facebook text post published: %s", post_id)
            return PublishResult(
                platform="facebook", status="published",
                external_post_id=post_id,
                external_url=f"https://www.facebook.com/{post_id}",
                published_at=now,
            )
        except Exception as exc:
            logger.error("Facebook publish failed: %s", exc)
            return PublishResult(platform="facebook", status="failed", error_message=str(exc)[:500], published_at=now)

    def _publish_photo(self, img_file, caption: str, page_id: str, token: str, now) -> PublishResult:
        # Step 1: Upload photo as unpublished to get a photo_id for a standalone feed post.
        # This prevents Facebook from bundling multiple photo uploads into one album story.
        upload_url = f"{GRAPH_API}/{page_id}/photos"
        try:
            with open(img_file, "rb") as f:
                upload_resp = httpx.post(
                    upload_url,
                    data={"published": "false", "access_token": token},
                    files={"source": (img_file.name, f, "image/jpeg")},
                    timeout=60,
                )

            upload_data = upload_resp.json() if upload_resp.headers.get("content-type", "").startswith("application/json") else {}
            logger.info("Photo upload response: %s", upload_data)

            if upload_resp.is_success:
                photo_id = upload_data.get("id") or upload_data.get("photo_id")
                # Validate: photo_id must be a numeric string and not the page_id itself
                if photo_id and str(photo_id) != str(page_id) and str(photo_id).isdigit():
                    # Step 2: Create a standalone feed post with the photo attached
                    feed_resp = httpx.post(
                        f"{GRAPH_API}/{page_id}/feed",
                        data={"message": caption, "object_attachment": photo_id, "access_token": token},
                        timeout=30,
                    )
                    if feed_resp.is_success:
                        post_id = feed_resp.json().get("id")
                        logger.info("Facebook photo post published (2-step): %s", post_id)
                        return PublishResult(
                            platform="facebook", status="published",
                            external_post_id=str(post_id),
                            external_url=f"https://www.facebook.com/{post_id}",
                            published_at=now,
                        )
                    logger.warning("2-step feed post failed (%d), falling back to direct photo post", feed_resp.status_code)
                else:
                    logger.warning("Invalid photo_id from upload (%s), falling back to direct photo post", photo_id)
            else:
                logger.warning("Photo upload failed (%d), falling back to direct photo post", upload_resp.status_code)

        except Exception as exc:
            logger.warning("2-step photo publish error: %s — falling back to direct photo post", exc)

        # Fallback: direct photo post (creates story immediately, may bundle with other photos)
        try:
            with open(img_file, "rb") as f:
                resp = httpx.post(
                    upload_url,
                    data={"caption": caption, "access_token": token},
                    files={"source": (img_file.name, f, "image/jpeg")},
                    timeout=60,
                )
            if not resp.is_success:
                fb_error = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else resp.text
                logger.error("Facebook photo API error %d: %s", resp.status_code, fb_error)
                return PublishResult(platform="facebook", status="failed", error_message=str(fb_error)[:500], published_at=now)
            post_id = resp.json().get("post_id") or resp.json().get("id")
            logger.info("Facebook photo post published (direct): %s", post_id)
            return PublishResult(
                platform="facebook", status="published",
                external_post_id=str(post_id),
                external_url=f"https://www.facebook.com/{post_id}",
                published_at=now,
            )
        except Exception as exc:
            logger.error("Facebook photo publish failed: %s", exc)
            return PublishResult(platform="facebook", status="failed", error_message=str(exc)[:500], published_at=now)
