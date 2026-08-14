"""
Structured logging powered by Loguru.

Replaces the default uvicorn / stdlib loggers with a single Loguru sink
so every log line is JSON-structured and routed through one pipeline.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger

from app.config import get_settings

if TYPE_CHECKING:
    from loguru import Record

# Remove default Loguru handler so we can reconfigure.
logger.remove()

_settings = get_settings()
_log_dir = Path(__file__).resolve().parent.parent.parent / "logs"
_log_dir.mkdir(parents=True, exist_ok=True)


def _sensitive_filter(record: Record) -> bool:
    """Prevent accidental logging of API keys."""
    msg = str(record.get("message", ""))
    if _settings.openrouter_api_key and _settings.openrouter_api_key in msg:
        record["message"] = msg.replace(_settings.openrouter_api_key, "***REDACTED***")
    return True


# Console sink — human-readable during development, JSON in production.
logger.add(
    sys.stderr,
    level=_settings.log_level.upper(),
    format=(
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> — "
        "<level>{message}</level>"
    ),
    filter=_sensitive_filter,
    colorize=True,
    backtrace=True,
    diagnose=not _settings.is_production,
)

# File sink — rotated daily, retained for 30 days.
logger.add(
    str(_log_dir / "app_{time:YYYY-MM-DD}.log"),
    level=_settings.log_level.upper(),
    rotation="00:00",
    retention="30 days",
    compression="gz",
    filter=_sensitive_filter,
    serialize=True,  # JSON lines
)


def get_logger(name: str = "leetcode_ai"):
    """Return a contextual logger bound with a module name."""
    return logger.bind(module=name)
