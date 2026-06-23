"""Extract article text from URLs using trafilatura with requests/BS4 fallback."""
from __future__ import annotations
import logging
from src import config
from src.models.schemas import SourceItem

logger = logging.getLogger(__name__)


def extract_content(source: SourceItem) -> SourceItem:
    """Return source with extracted_content and extraction_status filled in."""
    url = str(source.url)
    content = _try_trafilatura(url)
    if content and len(content) >= 100:
        return source.model_copy(update={
            "extracted_content": content[:config.MAX_EXTRACTED_CHARS_PER_SOURCE],
            "extraction_status": "success" if len(content) >= 300 else "partial",
        })

    content = _try_requests_bs4(url)
    if content and len(content) >= 100:
        return source.model_copy(update={
            "extracted_content": content[:config.MAX_EXTRACTED_CHARS_PER_SOURCE],
            "extraction_status": "partial",
        })

    fallback = source.snippet or "Không trích xuất được nội dung."
    return source.model_copy(update={
        "extracted_content": fallback,
        "extraction_status": "failed",
    })


def _try_trafilatura(url: str) -> str | None:
    try:
        import trafilatura
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            return None
        return trafilatura.extract(downloaded, include_comments=False, include_tables=False)
    except Exception as exc:
        logger.debug("trafilatura failed for %s: %s", url, exc)
        return None


def _try_requests_bs4(url: str) -> str | None:
    try:
        import requests
        from bs4 import BeautifulSoup
        resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        return " ".join(soup.get_text(separator=" ").split())
    except Exception as exc:
        logger.debug("requests/BS4 failed for %s: %s", url, exc)
        return None
