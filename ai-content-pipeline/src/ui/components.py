"""Reusable Streamlit UI components."""
from __future__ import annotations
import streamlit as st
from src import config
from src.utils.ffmpeg_utils import check_ffmpeg


def render_sidebar() -> None:
    """Render API status sidebar."""
    with st.sidebar:
        st.title("⚙️ Trạng thái hệ thống")
        st.markdown("---")

        _status("Tavily MCP", bool(config.TAVILY_API_KEY), "✅ Đã cấu hình (qua MCP)", "⚠️ Mock mode")
        _status("Anthropic Claude", bool(config.ANTHROPIC_API_KEY), "✅ Đã cấu hình", "⚠️ Mock mode")
        _status(
            "Facebook",
            bool(config.FACEBOOK_PAGE_ID and config.FACEBOOK_PAGE_ACCESS_TOKEN),
            "✅ Đăng thật",
            "🔶 Mock publish",
        )
        _status(
            "TikTok",
            bool(config.TIKTOK_ACCESS_TOKEN),
            "✅ Đăng thật",
            "🔶 Mock publish",
        )
        _status("FFmpeg", check_ffmpeg(), "✅ Sẵn sàng", "❌ Chưa cài — video sẽ bị bỏ qua")

        if not config.TAVILY_API_KEY or not config.ANTHROPIC_API_KEY:
            st.markdown("---")
            st.info("💡 Để dùng tính năng thật, hãy thêm API key vào file `.env`")

        st.markdown("---")
        if st.button("📋 Lịch sử job"):
            st.session_state["page"] = "history"
        if st.button("🏠 Trang chính"):
            st.session_state["page"] = "main"


def _status(label: str, ok: bool, ok_text: str, fail_text: str) -> None:
    if ok:
        st.success(f"**{label}**: {ok_text}")
    else:
        st.warning(f"**{label}**: {fail_text}")
