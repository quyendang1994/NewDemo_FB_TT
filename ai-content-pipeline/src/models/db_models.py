"""SQLAlchemy ORM models for SQLite persistence."""
from __future__ import annotations
from datetime import datetime
from sqlalchemy import String, Text, DateTime, Boolean, Integer, ForeignKey, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker
from src import config


class Base(DeclarativeBase):
    pass


class JobRecord(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    prompt: Mapped[str] = mapped_column(Text)
    language: Mapped[str] = mapped_column(String(20), default="vi")
    max_sources: Mapped[int] = mapped_column(Integer, default=5)
    generate_facebook: Mapped[bool] = mapped_column(Boolean, default=True)
    generate_tiktok: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(20), default="running")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    research_title: Mapped[str | None] = mapped_column(Text, nullable=True)
    research_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    facebook_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    tiktok_script: Mapped[str | None] = mapped_column(Text, nullable=True)
    video_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    sources: Mapped[list[SourceRecord]] = relationship("SourceRecord", back_populates="job", cascade="all, delete-orphan")
    publish_results: Mapped[list[PublishRecord]] = relationship("PublishRecord", back_populates="job", cascade="all, delete-orphan")


class SourceRecord(Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("jobs.id"))
    source_id: Mapped[str] = mapped_column(String(10))
    title: Mapped[str] = mapped_column(Text)
    url: Mapped[str] = mapped_column(Text)
    domain: Mapped[str] = mapped_column(String(200))
    extraction_status: Mapped[str] = mapped_column(String(20))
    retrieved_at: Mapped[datetime] = mapped_column(DateTime)
    published_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    content_preview: Mapped[str | None] = mapped_column(Text, nullable=True)

    job: Mapped[JobRecord] = relationship("JobRecord", back_populates="sources")


class PublishRecord(Base):
    __tablename__ = "publish_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("jobs.id"))
    platform: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(30))
    external_post_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    external_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime] = mapped_column(DateTime)

    job: Mapped[JobRecord] = relationship("JobRecord", back_populates="publish_results")


def get_engine():
    return create_engine(config.DATABASE_URL, connect_args={"check_same_thread": False})


def get_session_factory():
    engine = get_engine()
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)
