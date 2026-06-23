"""Text processing helpers."""
from __future__ import annotations
import re


def truncate(text: str, max_len: int = 100, suffix: str = "...") -> str:
    if len(text) <= max_len:
        return text
    return text[:max_len - len(suffix)] + suffix


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text)
