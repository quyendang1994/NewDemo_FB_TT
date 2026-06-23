"""Tests for URL and source deduplication."""
from datetime import datetime, timezone
from src.models.schemas import SourceItem
from src.services.source_deduplicator import deduplicate_sources, filter_poor_sources


def _src(sid: str, url: str, title: str, content: str = "x" * 200) -> SourceItem:
    return SourceItem(
        source_id=sid,
        title=title,
        url=url,  # type: ignore[arg-type]
        domain="example.com",
        retrieved_at=datetime.now(timezone.utc),
        extracted_content=content,
        extraction_status="success",
    )


def test_dedup_same_url():
    sources = [
        _src("S1", "https://example.com/a", "Article A"),
        _src("S2", "https://example.com/a", "Article A copy"),
    ]
    result = deduplicate_sources(sources)
    assert len(result) == 1


def test_dedup_same_title():
    sources = [
        _src("S1", "https://example.com/a", "Same Title"),
        _src("S2", "https://example.com/b", "Same Title"),
    ]
    result = deduplicate_sources(sources)
    assert len(result) == 1


def test_dedup_unique():
    sources = [_src(f"S{i}", f"https://example.com/{i}", f"Title {i}") for i in range(5)]
    result = deduplicate_sources(sources)
    assert len(result) == 5


def test_filter_poor_sources_removes_short():
    sources = [
        _src("S1", "https://a.com/1", "T1", "x" * 50),
        _src("S2", "https://a.com/2", "T2", "x" * 200),
    ]
    result = filter_poor_sources(sources, min_chars=100)
    assert len(result) == 1
    assert result[0].source_id == "S2"


def test_filter_keeps_all_when_all_long():
    sources = [_src(f"S{i}", f"https://a.com/{i}", f"T{i}", "x" * 300) for i in range(3)]
    result = filter_poor_sources(sources, min_chars=100)
    assert len(result) == 3
