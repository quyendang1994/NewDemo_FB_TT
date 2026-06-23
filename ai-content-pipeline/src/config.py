"""Application configuration loaded from environment variables."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / os.getenv("OUTPUT_DIR", "output")

DATA_DIR.mkdir(exist_ok=True)
(OUTPUT_DIR / "audio").mkdir(parents=True, exist_ok=True)
(OUTPUT_DIR / "images").mkdir(parents=True, exist_ok=True)
(OUTPUT_DIR / "videos").mkdir(parents=True, exist_ok=True)
(OUTPUT_DIR / "subtitles").mkdir(parents=True, exist_ok=True)

APP_ENV: str = os.getenv("APP_ENV", "development")
DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR}/app.db")

TAVILY_API_KEY: str | None = os.getenv("TAVILY_API_KEY")
ANTHROPIC_API_KEY: str | None = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_MODEL: str = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")

FACEBOOK_PAGE_ID: str | None = os.getenv("FACEBOOK_PAGE_ID")
FACEBOOK_PAGE_ACCESS_TOKEN: str | None = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN")

TIKTOK_CLIENT_KEY: str | None = os.getenv("TIKTOK_CLIENT_KEY")
TIKTOK_CLIENT_SECRET: str | None = os.getenv("TIKTOK_CLIENT_SECRET")
TIKTOK_ACCESS_TOKEN: str | None = os.getenv("TIKTOK_ACCESS_TOKEN")

MAX_EXTRACTED_CHARS_PER_SOURCE: int = int(os.getenv("MAX_EXTRACTED_CHARS_PER_SOURCE", "8000"))
MAX_SOURCES: int = int(os.getenv("MAX_SOURCES", "5"))
ENABLE_REAL_PUBLISHING: bool = os.getenv("ENABLE_REAL_PUBLISHING", "false").lower() == "true"
