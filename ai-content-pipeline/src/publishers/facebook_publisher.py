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
        import json as _json
        upload_url = f"{GRAPH_API}/{page_id}/photos"

        # Try two strategies to get a valid photo_id for a standalone feed post.
        # Both avoid creating a photo album story that Facebook bundles across runs.
        # Strategy A: no_story=true — photo lands in album but no news-feed story is created.
        # Strategy B: published=false — photo is staged/draft only, also no story.
        photo_id = None
        for label, extra_data in [("no_story", {"no_story": "true"}), ("unpublished", {"published": "false"})]:
            try:
                with open(img_file, "rb") as f:
                    up = httpx.post(
                        upload_url,
                        data={**extra_data, "access_token": token},
                        files={"source": (img_file.name, f, "image/jpeg")},
                        timeout=60,
                    )
                logger.info("[upload/%s] status=%d body=%s", label, up.status_code, up.text[:500])
                if up.is_success:
                    data = up.json() if "json" in up.headers.get("content-type", "") else {}
                    pid = str(data.get("id") or data.get("photo_id") or "")
                    if pid and pid != str(page_id) and pid.isdigit():
                        photo_id = pid
                        logger.info("[upload/%s] valid photo_id=%s", label, photo_id)
                        break
                    logger.warning("[upload/%s] bad photo_id=%r (page_id=%s)", label, pid, page_id)
            except Exception as exc:
                logger.warning("[upload/%s] error: %s", label, exc)

        if photo_id:
            # Try object_attachment first, then attached_media JSON format
            for feed_label, feed_data in [
                ("object_attachment", {"message": caption, "object_attachment": photo_id, "access_token": token}),
                ("attached_media", {"message": caption, "attached_media": _json.dumps([{"media_fbid": photo_id}]), "access_token": token}),
            ]:
                try:
                    feed = httpx.post(f"{GRAPH_API}/{page_id}/feed", data=feed_data, timeout=30)
                    logger.info("[feed/%s] status=%d body=%s", feed_label, feed.status_code, feed.text[:500])
                    if feed.is_success:
                        post_id = feed.json().get("id")
                        logger.info("Facebook photo post published (2-step/%s): %s", feed_label, post_id)
                        return PublishResult(
                            platform="facebook", status="published",
                            external_post_id=str(post_id),
                            external_url=f"https://www.facebook.com/{post_id}",
                            published_at=now,
                        )
                    logger.warning("[feed/%s] failed, trying next", feed_label)
                except Exception as exc:
                    logger.warning("[feed/%s] error: %s", feed_label, exc)

        # Fallback: direct photo post (creates album story — may bundle across pipeline runs)
        logger.warning("All 2-step strategies failed — falling back to direct photo post (may bundle)")
        try:
            with open(img_file, "rb") as f:
                resp = httpx.post(
                    upload_url,
                    data={"caption": caption, "access_token": token},
                    files={"source": (img_file.name, f, "image/jpeg")},
                    timeout=60,
                )
            logger.info("[direct] status=%d body=%s", resp.status_code, resp.text[:500])
            if not resp.is_success:
                fb_error = resp.json() if "json" in resp.headers.get("content-type", "") else resp.text
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
