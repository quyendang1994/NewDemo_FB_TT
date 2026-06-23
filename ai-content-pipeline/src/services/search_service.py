"""Web search via Tavily API with mock fallback."""
from __future__ import annotations
import logging
from datetime import datetime, timezone
from src import config
from src.models.schemas import SourceItem

logger = logging.getLogger(__name__)

MOCK_SOURCES: list[dict] = [
    {"title": "AI trong năm 2025: Xu hướng và triển vọng", "url": "https://example.com/ai-2025", "domain": "example.com", "snippet": "Trí tuệ nhân tạo đang phát triển với tốc độ chưa từng thấy..."},
    {"title": "Machine Learning và ứng dụng thực tế", "url": "https://techblog.example.com/ml-apps", "domain": "techblog.example.com", "snippet": "Machine Learning đã thâm nhập vào hầu hết các ngành công nghiệp..."},
    {"title": "ChatGPT và tương lai của AI hội thoại", "url": "https://news.example.com/chatgpt-future", "domain": "news.example.com", "snippet": "Các mô hình ngôn ngữ lớn đang định hình lại cách con người tương tác..."},
    {"title": "Đạo đức AI: Thách thức và giải pháp", "url": "https://research.example.com/ai-ethics", "domain": "research.example.com", "snippet": "Vấn đề đạo đức trong phát triển AI ngày càng được quan tâm..."},
    {"title": "Ứng dụng AI trong y tế Việt Nam", "url": "https://health.example.com/ai-vn", "domain": "health.example.com", "snippet": "Các bệnh viện tại Việt Nam đang thử nghiệm AI trong chẩn đoán bệnh..."},
]


def search_web(query: str, max_results: int = 5) -> list[dict]:
    """Search web using Tavily API; falls back to mock data if key not configured."""
    if not config.TAVILY_API_KEY:
        logger.warning("TAVILY_API_KEY not set — returning mock search results")
        return MOCK_SOURCES[:max_results]

    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=config.TAVILY_API_KEY)
        response = client.search(query=query, max_results=max_results, include_domains=[], exclude_domains=[])
        results = response.get("results", [])
        logger.info("Tavily returned %d results", len(results))
        return results
    except Exception as exc:
        logger.error("Tavily search failed: %s — falling back to mock", exc)
        return MOCK_SOURCES[:max_results]


def build_source_items(raw_results: list[dict]) -> list[SourceItem]:
    """Convert raw Tavily results into SourceItem list with S1..SN IDs."""
    items: list[SourceItem] = []
    for idx, r in enumerate(raw_results, start=1):
        url = r.get("url", "https://example.com")
        domain = url.split("/")[2] if "://" in url else url
        items.append(SourceItem(
            source_id=f"S{idx}",
            title=r.get("title", "Untitled"),
            url=url,  # type: ignore[arg-type]
            domain=domain,
            snippet=r.get("content", r.get("snippet")),
            retrieved_at=datetime.now(timezone.utc),
            extracted_content="",
            extraction_status="failed",
        ))
    return items
