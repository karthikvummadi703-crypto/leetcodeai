"""
Tests for the in-memory rate limiter and the chat endpoint integration.
"""

import asyncio
import time

import pytest
from app.core.rate_limit import RateLimiter, get_rate_limiter
from httpx import ASGITransport, AsyncClient

# ── Unit tests: RateLimiter ──────────────────────────────────────


def test_limiter_allows_within_budget():
    limiter = RateLimiter(max_requests=3, window_seconds=60)
    assert limiter.allow("u1") is True
    assert limiter.allow("u1") is True
    assert limiter.allow("u1") is True
    assert limiter.allow("u1") is False


def test_limiter_is_per_key():
    limiter = RateLimiter(max_requests=1, window_seconds=60)
    assert limiter.allow("u1") is True
    assert limiter.allow("u1") is False
    assert limiter.allow("u2") is True


def test_limiter_resets_after_window():
    limiter = RateLimiter(max_requests=1, window_seconds=0.3)
    assert limiter.allow("u1") is True
    assert limiter.allow("u1") is False
    time.sleep(0.4)
    assert limiter.allow("u1") is True


def test_limiter_reset_clears_hits():
    limiter = RateLimiter(max_requests=1, window_seconds=60)
    assert limiter.allow("u1") is True
    limiter.reset("u1")
    assert limiter.allow("u1") is True


def test_disabled_limiter_always_allows():
    limiter = RateLimiter(max_requests=1, window_seconds=60, enabled=False)
    for _ in range(5):
        assert limiter.allow("u1") is True


# ── Endpoint integration: 429 on budget exhaustion ───────────────


@pytest.mark.asyncio
async def test_chat_endpoint_returns_429_when_rate_limited(monkeypatch):
    from app.api import chat as chat_module
    from app.auth import get_current_user
    from app.schemas import UserProfile
    from app.services.conversation_memory import create_conversation
    from main import app

    class StubAgent:
        async def run(self, conversation, user_message):
            return type("R", (), {"content": "ok"})()

        async def run_stream(self, conversation, user_message):
            yield "ok"

    async def fake_user() -> UserProfile:
        return UserProfile(uid="rl-user", email="rl@test.com")

    conv = create_conversation("rl-user", "RL Conv")

    limiter = get_rate_limiter()
    original_enabled = limiter.enabled
    original_max = limiter.max_requests
    limiter.enabled = True
    limiter.max_requests = 2
    limiter.reset("rl-user")

    app.dependency_overrides[get_current_user] = fake_user
    monkeypatch.setattr(chat_module, "_agent", StubAgent())

    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            payload = {"conversation_id": conv.id, "message": "hi", "stream": False}
            first = await client.post("/api/chat", json=payload)
            second = await client.post("/api/chat", json=payload)
            third = await client.post("/api/chat", json=payload)

        assert first.status_code == 200
        assert second.status_code == 200
        assert third.status_code == 429
        assert third.json()["success"] is False
        assert "error" in third.json()
    finally:
        limiter.enabled = original_enabled
        limiter.max_requests = original_max
        limiter.reset("rl-user")
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_rate_limiter_async_usage():
    limiter = RateLimiter(max_requests=1, window_seconds=60)
    results = await asyncio.gather(
        asyncio.to_thread(limiter.allow, "k"),
        asyncio.to_thread(limiter.allow, "k"),
    )
    assert results.count(True) == 1
    assert results.count(False) == 1
