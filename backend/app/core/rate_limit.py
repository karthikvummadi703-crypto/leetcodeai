"""
In-memory sliding-window rate limiter.

Protects cost-sensitive endpoints (``POST /chat``, ``POST /new-chat``)
against abuse with a per-user request cap over a rolling window. The
window is keyed by the authenticated user's UID so a single account can
never exceed the configured budget regardless of IP.

Notes for production:
  * State lives in process memory. On Railway (single container) this is
    accurate; if you scale to multiple replicas, swap this for a shared
    store (e.g. Redis) or add a platform-level limiter in front.
  * Disabled via ``RATE_LIMIT_ENABLED=false`` (used by the test suite).
"""

from __future__ import annotations

import threading
import time

from fastapi import Depends

from app.auth import get_current_user
from app.config import get_settings
from app.core import RateLimitError, get_logger
from app.schemas import UserProfile

log = get_logger("rate_limit")


class RateLimiter:
    """Sliding-window limiter storing request timestamps per key."""

    def __init__(
        self,
        max_requests: int = 20,
        window_seconds: float = 60.0,
        enabled: bool = True,
    ) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.enabled = enabled
        self._hits: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        """
        Record a request for ``key`` and report whether it is permitted.

        Returns ``True`` when the request is within the budget (and records
        it), ``False`` when the budget is exhausted. Disabled limiters
        always return ``True`` without recording anything.
        """
        if not self.enabled:
            return True

        now = time.monotonic()
        cutoff = now - self.window_seconds

        with self._lock:
            window = self._hits.setdefault(key, [])
            # Drop timestamps that fell out of the window.
            while window and window[0] <= cutoff:
                window.pop(0)
            if len(window) >= self.max_requests:
                log.warning(
                    "Rate limit exceeded for key={key} ({n}/{max} in {window}s)",
                    key=key,
                    n=len(window),
                    max=self.max_requests,
                    window=self.window_seconds,
                )
                return False
            window.append(now)
            return True

    def reset(self, key: str | None = None) -> None:
        """Clear recorded hits for ``key`` (or everything when omitted)."""
        with self._lock:
            if key is None:
                self._hits.clear()
            else:
                self._hits.pop(key, None)


def _build_limiter() -> RateLimiter:
    settings = get_settings()
    return RateLimiter(
        max_requests=settings.rate_limit_max_requests,
        window_seconds=settings.rate_limit_window_seconds,
        enabled=settings.rate_limit_enabled,
    )


_limiter: RateLimiter = _build_limiter()


def get_rate_limiter() -> RateLimiter:
    """Return the shared rate-limiter singleton."""
    return _limiter


def enforce_rate_limit(user: UserProfile = Depends(get_current_user)) -> UserProfile:
    """
    FastAPI dependency — apply the per-user rate limit for the current
    request. Runs after authentication so the limit is keyed by UID and
    anonymous traffic is still rejected with 401 first.

    Raise :class:`RateLimitError` (429) when the budget is exhausted.
    """
    if get_rate_limiter().allow(user.uid):
        return user
    raise RateLimitError("Too many requests. Please slow down and try again in a moment.")
