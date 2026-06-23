"""Main research & content generation page."""
from __future__ import annotations
import uuid
import logging
from datetime import datetime, timezone
import streamlit as st
from src.models.schemas import PipelineJob
from src.services import research_service, content_generation_service, storage_service, video_builder
from src.publishers.facebook_publisher import FacebookPublisher
from src.publishers.tiktok_publisher import TikTokPublisher

logger = logging.getLogger(__name__)


def render() -> None:
    st.title("🤖 AI Content Pipeline")
    st.caption("Nghiên cứu web → Tổng hợp → Tạo nội dung Facebook & TikTok")

    with st.form("research_form"):
        prompt = st.text_area(
            "📝 Chủ đề / Prompt",
            placeholder="Ví dụ: Xu hướng AI năm 2025 tại Việt Nam",
            height=100,
        )
        col1, col2 = st.columns(2)
        with col1:
            language = st.selectbox(
                "🌐 Ngôn ngữ đầu ra",
                ["vi", "en"],
                index=0,
                format_func=lambda x: "Tiếng Việt" if x == "vi" else "English",
            )
            max_sources = st.slider("📚 Số nguồn tối đa", 3, 10, 5)
        with col2:
            gen_facebook = st.checkbox("📘 Tạo Facebook post", value=True)
            gen_tiktok = st.checkbox("🎵 Tạo TikTok video", value=True)
        submitted = st.form_submit_button("🔍 Nghiên cứu & Tạo nội dung", use_container_width=True)

    if submitted:
        if not prompt.strip():
            st.error("Vui lòng nhập chủ đề.")
            return
        _run_pipeline(prompt.strip(), language, max_sources, gen_facebook, gen_tiktok)

    if "current_job" in st.session_state:
        _render_results()


def _run_pipeline(
    prompt: str,
    language: str,
    max_sources: int,
    gen_facebook: bool,
    gen_tiktok: bool,
) -> None:
    job_id = str(uuid.uuid4())
    job = PipelineJob(
        job_id=job_id,
        prompt=prompt,
        language=language,
        max_sources=max_sources,
        generate_facebook=gen_facebook,
        generate_tiktok=gen_tiktok,
        created_at=datetime.now(timezone.utc),
        status="running",
    )

    progress = st.progress(0, "Khởi động...")
    try:
        progress.progress(10, "🔍 Tìm kiếm nguồn...")
        sources, research = research_service.run_research(prompt, language, max_sources)
        job = job.model_copy(update={"sources": sources, "research": research})
        storage_service.save_job(job)

        progress.progress(50, "✍️ Tạo nội dung...")
        content = content_generation_service.generate_social_content(
            research, sources, language, gen_facebook, gen_tiktok
        )
        job = job.model_copy(update={"content": content})
        storage_service.save_job(job)

        video_path: str | None = None
        if gen_tiktok:
            progress.progress(70, "🎬 Dựng video TikTok...")
            try:
                video_path = video_builder.build_video(content.tiktok, job_id, language)
            except Exception as e:
                logger.warning("Video build failed: %s", e)
            job = job.model_copy(update={"video_path": video_path})

        job = job.model_copy(update={"status": "done"})
        storage_service.save_job(job)
        st.session_state["current_job"] = job
        progress.progress(100, "✅ Hoàn thành!")
        st.rerun()
    except Exception as exc:
        progress.empty()
        job = job.model_copy(update={"status": "failed"})
        storage_service.save_job(job)
        st.error(f"Lỗi: {exc}")
        logger.exception("Pipeline failed for job %s", job_id)


def _render_results() -> None:
    job: PipelineJob = st.session_state["current_job"]
    st.markdown("---")
    st.subheader("📋 Nguồn tham khảo")

    for s in job.sources:
        with st.expander(f"[{s.source_id}] {s.title[:80]}"):
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Domain:** {s.domain}")
                st.write(f"**Lấy lúc:** {s.retrieved_at.strftime('%H:%M %d/%m/%Y')}")
            with col2:
                pub = s.published_date.strftime("%d/%m/%Y") if s.published_date else "Không rõ"
                st.write(f"**Xuất bản:** {pub}")
                status_icon = {"success": "✅", "partial": "⚠️", "failed": "❌"}.get(
                    s.extraction_status, "?"
                )
                st.write(f"**Trạng thái:** {status_icon} {s.extraction_status}")
            st.markdown(f"[🔗 Mở link]({s.url})")
            if s.extracted_content:
                preview = s.extracted_content[:500]
                if len(s.extracted_content) > 500:
                    preview += "..."
                st.text(preview)

    st.markdown("---")
    tabs = st.tabs(
        ["📊 Tóm tắt nghiên cứu", "📘 Facebook Draft", "🎵 TikTok Draft", "🎬 Video", "🚀 Đăng bài"]
    )
    _tab_research(tabs[0], job)
    _tab_facebook(tabs[1], job)
    _tab_tiktok(tabs[2], job)
    _tab_video(tabs[3], job)
    _tab_publish(tabs[4], job)


def _tab_research(tab: object, job: PipelineJob) -> None:
    with tab:  # type: ignore[attr-defined]
        if not job.research:
            st.info("Chưa có dữ liệu nghiên cứu.")
            return
        r = job.research
        st.subheader(r.title)
        st.write(r.short_summary)
        st.markdown("**Điểm chính:**")
        for kp in r.key_points:
            st.markdown(f"- {kp}")
        with st.expander("Chi tiết"):
            st.write(r.detailed_summary)
        if r.uncertainties:
            st.warning("**Điểm chưa chắc chắn:**\n" + "\n".join(f"- {u}" for u in r.uncertainties))


def _tab_facebook(tab: object, job: PipelineJob) -> None:
    with tab:  # type: ignore[attr-defined]
        if not job.content:
            st.info("Chưa có nội dung Facebook.")
            return
        fb = job.content.facebook
        new_title = st.text_input("Tiêu đề", value=fb.title, key="fb_title")
        new_body = st.text_area("Nội dung", value=fb.body, height=200, key="fb_body")
        new_hashtags = st.text_input(
            "Hashtag (cách nhau bằng dấu cách)", value=" ".join(fb.hashtags), key="fb_hashtags"
        )
        updated_fb = fb.model_copy(
            update={"title": new_title, "body": new_body, "hashtags": new_hashtags.split()}
        )
        job.content = job.content.model_copy(update={"facebook": updated_fb})
        st.session_state["current_job"] = job


def _tab_tiktok(tab: object, job: PipelineJob) -> None:
    with tab:  # type: ignore[attr-defined]
        if not job.content:
            st.info("Chưa có nội dung TikTok.")
            return
        tk = job.content.tiktok
        new_hook = st.text_input("Hook", value=tk.hook, key="tk_hook")
        new_script = st.text_area("Kịch bản", value=tk.narration_script, height=150, key="tk_script")
        new_caption = st.text_input("Caption", value=tk.caption, key="tk_caption")
        new_hashtags = st.text_input("Hashtag", value=" ".join(tk.hashtags), key="tk_hashtags")
        st.markdown("**Cảnh quay:**")
        for scene in tk.scenes:
            st.markdown(
                f"**Cảnh {scene.scene_number}** ({scene.duration_seconds}s): {scene.on_screen_text}"
            )
        updated_tk = tk.model_copy(
            update={
                "hook": new_hook,
                "narration_script": new_script,
                "caption": new_caption,
                "hashtags": new_hashtags.split(),
            }
        )
        job.content = job.content.model_copy(update={"tiktok": updated_tk})
        st.session_state["current_job"] = job


def _tab_video(tab: object, job: PipelineJob) -> None:
    with tab:  # type: ignore[attr-defined]
        from src.utils.ffmpeg_utils import check_ffmpeg

        if not check_ffmpeg():
            st.warning("⚠️ FFmpeg chưa được cài đặt. Cài FFmpeg để tạo video TikTok.")
            return
        if job.video_path:
            st.success(f"✅ Video đã tạo: {job.video_path}")
            try:
                with open(job.video_path, "rb") as f:
                    st.video(f.read())
            except Exception:
                st.info("Không thể preview video trong browser.")
        else:
            st.info("Video chưa được tạo hoặc quá trình tạo thất bại.")


def _tab_publish(tab: object, job: PipelineJob) -> None:
    with tab:  # type: ignore[attr-defined]
        confirmed = st.checkbox(
            "✅ Tôi đã xem và xác nhận nội dung trước khi đăng", key="confirm_publish"
        )
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📘 Đăng Facebook", disabled=not confirmed):
                if not job.content:
                    st.error("Chưa có nội dung để đăng.")
                    return
                publisher = FacebookPublisher()
                result = publisher.publish(job.content.facebook)
                storage_service.save_publish_result(job.job_id, result)
                if result.status == "mock_published":
                    st.info("🔶 Mock publish Facebook (chưa có credentials thật)")
                elif result.status == "published":
                    st.success(f"✅ Đã đăng Facebook: {result.external_url}")
                else:
                    st.error(f"❌ Lỗi: {result.error_message}")
        with col2:
            if st.button("🎵 Upload TikTok", disabled=not confirmed):
                publisher = TikTokPublisher()
                result = publisher.publish(job.video_path)
                storage_service.save_publish_result(job.job_id, result)
                if result.status == "mock_published":
                    st.info("🔶 Mock publish TikTok (chưa có credentials thật)")
                elif result.status in ("published", "uploaded_private"):
                    st.success(f"✅ Upload TikTok thành công. ID: {result.external_post_id}")
                else:
                    st.error(f"❌ Lỗi: {result.error_message}")
