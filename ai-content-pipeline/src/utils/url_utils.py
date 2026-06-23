"""URL normalization and validation helpers."""
from __future__ import annotations
import re
from urllib.parse import urlparse


def extract_domain(url: str) -> str:
    try:
        return urlparse(url).netloc or url
    except Exception:
        return url


def is_valid_url(url: str) -> bool:
    return bool(re.match(r"https?://", url))


def normalize_url(url: str) -> str:
    url = url.rstrip("/").lower()
    url = re.sub(r"^https?://www\.", "https://", url)
    return url
