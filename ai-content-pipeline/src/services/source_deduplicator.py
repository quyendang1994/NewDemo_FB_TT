"""Remove duplicate and near-duplicate sources."""
from __future__ import annotations
import re
from src.models.schemas import SourceItem


def _normalize(text: str) -> str:
    return re.sub(r"\W+", " ", text.lower()).strip()


def deduplicate_sources(sources: list[SourceItem]) -> list[SourceItem]:
    """Remove sources with duplicate URLs or very similar titles."""
    seen_urls: set[str] = set()
    seen_titles: set[str] = set()
    unique: list[SourceItem] = []
    for s in sources:
        norm_url = _normalize(str(s.url))
        norm_title = _normalize(s.title)
        if norm_url in seen_urls:
            continue
        if norm_title in seen_titles:
            continue
        seen_urls.add(norm_url)
        seen_titles.add(norm_title)
        unique.append(s)
    return unique


def filter_poor_sources(sources: list[SourceItem], min_chars: int = 100) -> list[SourceItem]:
    """Remove sources with too little content."""
    return [s for s in sources if len(s.extracted_content) >= min_chars]
