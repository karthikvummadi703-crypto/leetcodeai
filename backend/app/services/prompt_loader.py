"""
Prompt loading service.

Reads all markdown prompt files from the prompts/ directory
and concatenates them into a single system prompt.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from app.core import get_logger

log = get_logger("prompt_loader")

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"

# Ordered list of prompt files to concatenate.
_PROMPT_FILES = [
    "system_prompt.md",
    "mentor_prompt.md",
    "coding_rules.md",
]


@lru_cache(maxsize=1)
def load_system_prompt() -> str:
    """
    Load and concatenate all prompt markdown files into a single string.

    Files are read in the order specified in _PROMPT_FILES.
    Any missing file is skipped with a warning.
    """
    parts: list[str] = []

    for filename in _PROMPT_FILES:
        filepath = PROMPTS_DIR / filename
        if not filepath.exists():
            log.warning("Prompt file not found: {path}", path=filepath)
            continue
        content = filepath.read_text(encoding="utf-8").strip()
        if content:
            parts.append(content)
            log.debug(
                "Loaded prompt: {filename} ({chars} chars)", filename=filename, chars=len(content)
            )

    combined = "\n\n---\n\n".join(parts)
    log.info(
        "System prompt assembled: {total} chars from {count} files",
        total=len(combined),
        count=len(parts),
    )
    return combined
