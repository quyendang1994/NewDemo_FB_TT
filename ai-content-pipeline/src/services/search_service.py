"""Web search via Tavily MCP server with mock fallback."""
from __future__ import annotations
import asyncio
import json
import logging
import os
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


async def _search_via_mcp(query: str, max_results: int) -> list[dict]:
    """Spawn Tavily MCP server via npx and call its search tool."""
    from mcp import ClientSession
    from mcp.client.stdio import StdioServerParameters, stdio_client

    env = {**os.environ, "TAVILY_API_KEY": config.TAVILY_API_KEY or ""}
    server_params = StdioServerParameters(
        command="npx",
        args=["-y", "tavily-mcp@latest"],
        env=env,
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Discover tool name dynamically (may be "tavily-search" or "tavily_search")
            tools_response = await session.list_tools()
            search_tool = next(
                (t for t in tools_response.tools if "search" in t.name.lower()),
                None,
            )
            if search_tool is None:
                raise RuntimeError("No search tool found in Tavily MCP server")

            logger.info("Using MCP tool: %s", search_tool.name)
            result = await session.call_tool(
                search_tool.name,
                arguments={"query": query, "max_results": max_results},
            )

    # Parse MCP text content → list[dict]
    results: list[dict] = []
    for content in result.content:
        text = getattr(content, "text", None)
        if not text:
            continue
        try:
            data = json.loads(text)
            if isinstance(data, list):
                results.extend(data)
            elif isinstance(data, dict):
                results.extend(data.get("results", []))
        except json.JSONDecodeError:
            # Tavily MCP may return plain text: "Title: ...\nURL: ...\nContent: ..."
            parsed = _parse_text_results(text)
            if parsed:
                results.extend(parsed)
            else:
                logger.warning("Non-JSON MCP response (first 200 chars): %s", text[:200])

    return results


def _parse_text_results(text: str) -> list[dict]:
    """Parse Tavily MCP plain-text response (Title/URL/Content blocks) into dicts."""
    import re
    results: list[dict] = []
    blocks = re.split(r"\n(?=Title:)", text.strip())
    for block in blocks:
        item: dict = {}
        content_lines: list[str] = []
        in_content = False
        for line in block.splitlines():
            if line.startswith("Title:"):
                item["title"] = line[6:].strip()
                in_content = False
            elif line.startswith("URL:"):
                item["url"] = line[4:].strip()
                in_content = False
            elif line.startswith("Content:"):
                content_lines = [line[8:].strip()]
                in_content = True
            elif in_content:
                content_lines.append(line)
        if content_lines:
            item["content"] = "\n".join(content_lines).strip()
        if "url" in item:
            results.append(item)
    return results


def search_web(query: str, max_results: int = 5) -> list[dict]:
    """Search web via Tavily MCP server; falls back to mock data if key not configured."""
    if not config.TAVILY_API_KEY:
        logger.warning("TAVILY_API_KEY not set — returning mock search results")
        return MOCK_SOURCES[:max_results]

    try:
        results = asyncio.run(_search_via_mcp(query, max_results))
        logger.info("Tavily MCP returned %d results", len(results))
        return results or MOCK_SOURCES[:max_results]
    except Exception as exc:
        logger.error("Tavily MCP search failed: %s — falling back to mock", exc)
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
