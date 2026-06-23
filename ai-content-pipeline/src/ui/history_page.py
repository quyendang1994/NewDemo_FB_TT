"""Job history page."""
from __future__ import annotations
import streamlit as st
from src.services import storage_service
from src.utils.text_utils import truncate


def render() -> None:
    st.title("📋 Lịch sử job")
    jobs = storage_service.list_jobs(limit=50)
    if not jobs:
        st.info("Chưa có job nào được chạy.")
        return

    for job in jobs:
        status_icon = {"done": "✅", "running": "⏳", "failed": "❌"}.get(job.status, "?")
        platforms = list({pr.platform for pr in job.publish_results})
        platform_text = ", ".join(platforms) if platforms else "—"

        with st.expander(
            f"{status_icon} [{job.created_at.strftime('%d/%m/%Y %H:%M')}] {truncate(job.prompt, 60)}"
        ):
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Trạng thái:** {job.status}")
                st.write(f"**Nền tảng đã đăng:** {platform_text}")
            with col2:
                st.write(f"**Ngôn ngữ:** {job.language}")
                st.write(f"**Nguồn yêu cầu:** {job.max_sources}")

            if job.research_title:
                st.write(f"**Tiêu đề:** {job.research_title}")
            if job.research_summary:
                st.write(f"**Tóm tắt:** {truncate(job.research_summary, 200)}")

            for pr in job.publish_results:
                if pr.status in ("published", "uploaded_private"):
                    icon = "✅"
                elif "mock" in pr.status:
                    icon = "🔶"
                else:
                    icon = "❌"
                line = f"{icon} {pr.platform}: {pr.status}"
                if pr.external_url:
                    line += f" — {pr.external_url}"
                st.write(line)
