"""Orchestrates search → extract → deduplicate → LLM research synthesis."""
from __future__ import annotations
import logging
from src.models.schemas import SourceItem, ResearchResult
from src.services import search_service, content_extractor, source_deduplicator, llm_service
from src.prompts import load_prompt
from src import config

logger = logging.getLogger(__name__)


def run_research(
    prompt: str,
    language: str = "vi",
    max_sources: int = 5,
) -> tuple[list[SourceItem], ResearchResult]:
    """Full research pipeline: search → extract → deduplicate → synthesize."""
    logger.info("Starting research for: %s", prompt[:80])

    raw = search_service.search_web(prompt, max_results=max_sources + 3)
    sources = search_service.build_source_items(raw)
    sources = source_deduplicator.deduplicate_sources(sources)
    sources = sources[:max_sources + 2]

    extracted: list[SourceItem] = []
    for s in sources:
        updated = content_extractor.extract_content(s)
        extracted.append(updated)
        logger.info("Extracted [%s] %s → %s", updated.source_id, updated.domain, updated.extraction_status)

    good_sources = source_deduplicator.filter_poor_sources(extracted)
    if not good_sources:
        good_sources = extracted[:3]  # fallback: keep at least some

    # Re-number sources sequentially
    final_sources = [
        s.model_copy(update={"source_id": f"S{i}"})
        for i, s in enumerate(good_sources[:max_sources], start=1)
    ]

    source_context = _build_source_context(final_sources)
    system_prompt = load_prompt("research_system_prompt.txt")
    user_message = f"Ngôn ngữ đầu ra: {language}\n\nChủ đề: {prompt}\n\n{source_context}"

    raw_result = llm_service.call_llm(system_prompt, user_message)
    raw_result["user_prompt"] = prompt
    result = ResearchResult(**raw_result)

    logger.info("Research done. Title: %s", result.title[:60])
    return final_sources, result


def _build_source_context(sources: list[SourceItem]) -> str:
    parts = ["=== SOURCES ==="]
    for s in sources:
        parts.append(f"[{s.source_id}] {s.title}\nURL: {s.url}\nDomain: {s.domain}\n{s.extracted_content[:1500]}\n---")
    return "\n".join(parts)
