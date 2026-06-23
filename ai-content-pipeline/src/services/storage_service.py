"""Persist and retrieve pipeline jobs via SQLAlchemy/SQLite."""
from __future__ import annotations
import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session, joinedload
from src.models.db_models import JobRecord, SourceRecord, PublishRecord, get_session_factory
from src.models.schemas import PipelineJob, PublishResult

logger = logging.getLogger(__name__)

_session_factory = None


def _get_session() -> Session:
    global _session_factory
    if _session_factory is None:
        _session_factory = get_session_factory()
    return _session_factory()


def save_job(job: PipelineJob) -> None:
    with _get_session() as session:
        record = session.get(JobRecord, job.job_id)
        if record is None:
            record = JobRecord(id=job.job_id)
            session.add(record)
        record.prompt = job.prompt
        record.language = job.language
        record.max_sources = job.max_sources
        record.generate_facebook = job.generate_facebook
        record.generate_tiktok = job.generate_tiktok
        record.status = job.status
        record.updated_at = datetime.now(timezone.utc)
        if job.research:
            record.research_title = job.research.title
            record.research_summary = job.research.short_summary
        if job.content:
            record.facebook_body = job.content.facebook.body
            record.tiktok_script = job.content.tiktok.narration_script
        record.video_path = job.video_path

        existing_source_ids = {str(s.source_id) for s in record.sources}
        for s in job.sources:
            if s.source_id not in existing_source_ids:
                record.sources.append(SourceRecord(
                    job_id=job.job_id,
                    source_id=s.source_id,
                    title=s.title,
                    url=str(s.url),
                    domain=s.domain,
                    extraction_status=s.extraction_status,
                    retrieved_at=s.retrieved_at,
                    published_date=s.published_date,
                    content_preview=s.extracted_content[:500] if s.extracted_content else None,
                ))

        session.commit()


def save_publish_result(job_id: str, result: PublishResult) -> None:
    with _get_session() as session:
        session.add(PublishRecord(
            job_id=job_id,
            platform=result.platform,
            status=result.status,
            external_post_id=result.external_post_id,
            external_url=result.external_url,
            error_message=result.error_message,
            published_at=result.published_at,
        ))
        session.commit()


def list_jobs(limit: int = 50) -> list[JobRecord]:
    with _get_session() as session:
        return (
            session.query(JobRecord)
            .options(joinedload(JobRecord.publish_results), joinedload(JobRecord.sources))
            .order_by(JobRecord.created_at.desc())
            .limit(limit)
            .all()
        )


def get_job(job_id: str) -> JobRecord | None:
    with _get_session() as session:
        return (
            session.query(JobRecord)
            .options(joinedload(JobRecord.publish_results), joinedload(JobRecord.sources))
            .filter(JobRecord.id == job_id)
            .first()
        )
