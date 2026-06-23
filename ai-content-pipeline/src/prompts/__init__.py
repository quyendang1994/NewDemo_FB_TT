from pathlib import Path

_PROMPTS_DIR = Path(__file__).parent


def load_prompt(filename: str) -> str:
    """Load a prompt text file from the prompts directory."""
    path = _PROMPTS_DIR / filename
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""
