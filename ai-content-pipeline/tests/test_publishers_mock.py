"""Tests for publisher mock mode when credentials are missing."""
from unittest.mock import patch
from src.publishers.facebook_publisher import FacebookPublisher
from src.publishers.tiktok_publisher import TikTokPublisher
from src.models.schemas import FacebookPost


def make_fb_post() -> FacebookPost:
    return FacebookPost(
        title="Test Title",
        body="Test body content",
        hashtags=["#AI"],
        source_references=["[S1] https://example.com"],
    )


def test_facebook_mock_when_no_credentials():
    import src.publishers.facebook_publisher as fb_mod
    original_id = fb_mod.config.FACEBOOK_PAGE_ID
    original_token = fb_mod.config.FACEBOOK_PAGE_ACCESS_TOKEN
    original_real = fb_mod.config.ENABLE_REAL_PUBLISHING
    try:
        fb_mod.config.FACEBOOK_PAGE_ID = None  # type: ignore[assignment]
        fb_mod.config.FACEBOOK_PAGE_ACCESS_TOKEN = None  # type: ignore[assignment]
        fb_mod.config.ENABLE_REAL_PUBLISHING = False  # type: ignore[assignment]
        publisher = FacebookPublisher()
        assert not publisher.is_configured
        result = publisher.publish(make_fb_post())
        assert result.status == "mock_published"
        assert result.platform == "facebook"
    finally:
        fb_mod.config.FACEBOOK_PAGE_ID = original_id  # type: ignore[assignment]
        fb_mod.config.FACEBOOK_PAGE_ACCESS_TOKEN = original_token  # type: ignore[assignment]
        fb_mod.config.ENABLE_REAL_PUBLISHING = original_real  # type: ignore[assignment]


def test_tiktok_mock_when_no_credentials():
    import src.publishers.tiktok_publisher as tk_mod
    original_token = tk_mod.config.TIKTOK_ACCESS_TOKEN
    original_key = tk_mod.config.TIKTOK_CLIENT_KEY
    original_real = tk_mod.config.ENABLE_REAL_PUBLISHING
    try:
        tk_mod.config.TIKTOK_ACCESS_TOKEN = None  # type: ignore[assignment]
        tk_mod.config.TIKTOK_CLIENT_KEY = None  # type: ignore[assignment]
        tk_mod.config.ENABLE_REAL_PUBLISHING = False  # type: ignore[assignment]
        publisher = TikTokPublisher()
        assert not publisher.is_configured
        result = publisher.publish(None)
        assert result.status == "mock_published"
        assert result.platform == "tiktok"
    finally:
        tk_mod.config.TIKTOK_ACCESS_TOKEN = original_token  # type: ignore[assignment]
        tk_mod.config.TIKTOK_CLIENT_KEY = original_key  # type: ignore[assignment]
        tk_mod.config.ENABLE_REAL_PUBLISHING = original_real  # type: ignore[assignment]


def test_facebook_no_secret_in_error():
    """Error messages must not leak the access token."""
    import src.publishers.facebook_publisher as fb_mod
    original_id = fb_mod.config.FACEBOOK_PAGE_ID
    original_token = fb_mod.config.FACEBOOK_PAGE_ACCESS_TOKEN
    original_real = fb_mod.config.ENABLE_REAL_PUBLISHING
    try:
        fb_mod.config.FACEBOOK_PAGE_ID = "123456"  # type: ignore[assignment]
        fb_mod.config.FACEBOOK_PAGE_ACCESS_TOKEN = "SECRET_TOKEN_VALUE"  # type: ignore[assignment]
        fb_mod.config.ENABLE_REAL_PUBLISHING = True  # type: ignore[assignment]
        with patch("httpx.post", side_effect=Exception("network error")):
            publisher = FacebookPublisher()
            result = publisher.publish(make_fb_post())
            assert result.status == "failed"
            assert "SECRET_TOKEN_VALUE" not in (result.error_message or "")
    finally:
        fb_mod.config.FACEBOOK_PAGE_ID = original_id  # type: ignore[assignment]
        fb_mod.config.FACEBOOK_PAGE_ACCESS_TOKEN = original_token  # type: ignore[assignment]
        fb_mod.config.ENABLE_REAL_PUBLISHING = original_real  # type: ignore[assignment]
