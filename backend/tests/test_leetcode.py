"""
Tests for the LeetCode account integration endpoints.

LeetCode network calls are fully stubbed so the suite stays offline.
"""

import pytest
from httpx import AsyncClient, ASGITransport

from main import app
from app.auth import get_current_user
from app.leetcode.client import LeetCodeError, UserNotFoundError
from app.schemas import UserProfile
from app.api import leetcode as leetcode_module


PROFILE = {
    "username": "rock",
    "real_name": "Rock Lee",
    "avatar": "https://example.com/a.png",
    "ranking": 7704,
    "reputation": 1200,
    "country": "USA",
    "school": "Hidden Leaf",
    "accepted": {"easy": 10, "medium": 5, "hard": 1, "total": 16},
    "total_submissions": {"easy": 20, "medium": 12, "hard": 4, "total": 36},
}

SNAPSHOT = {
    **PROFILE,
    "progress": {
        "accepted": PROFILE["accepted"],
        "failed": {"easy": 1, "medium": 2, "hard": 0, "total": 3},
        "untouched": {"easy": 900, "medium": 2000, "hard": 950, "total": 3850},
    },
    "recent_ac": [
        {"id": "1", "title": "Two Sum", "title_slug": "two-sum", "timestamp": 1700000000},
        {"id": "2", "title": "Valid Parentheses", "title_slug": "valid-parentheses", "timestamp": 1700000001},
    ],
    "languages": [{"language": "Python3", "problems_solved": 12}],
    "contest": {"contests_attended": 3, "rating": 1500, "global_ranking": 50000, "top_percentage": 10.0},
}


class StubLeetCodeClient:
    async def get_profile(self, username: str) -> dict:
        if username == "missing":
            raise UserNotFoundError(username)
        if username == "down":
            raise LeetCodeError("network down")
        return PROFILE

    async def get_progress(self, username: str) -> dict:
        return SNAPSHOT["progress"]

    async def get_recent_ac_submissions(self, username: str, limit: int = 20) -> list:
        return SNAPSHOT["recent_ac"]

    async def get_language_stats(self, username: str) -> list:
        return SNAPSHOT["languages"]

    async def get_contest_ranking(self, username: str) -> dict | None:
        return SNAPSHOT["contest"]

    async def fetch_user_snapshot(self, username: str) -> dict:
        if username == "missing":
            raise UserNotFoundError(username)
        if username == "down":
            raise LeetCodeError("network down")
        return SNAPSHOT


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(leetcode_module, "_client", StubLeetCodeClient())

    async def fake_user() -> UserProfile:
        return UserProfile(uid="lc-user", email="lc@test.com")

    app.dependency_overrides[get_current_user] = fake_user
    transport = ASGITransport(app=app)
    yield AsyncClient(transport=transport, base_url="http://test")
    app.dependency_overrides.clear()
    leetcode_module.clear_leetcode_username("lc-user")


@pytest.mark.asyncio
async def test_status_before_linking(client):
    async with client as c:
        resp = await c.get("/api/leetcode/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["enabled"] is False
        assert data["username"] is None


@pytest.mark.asyncio
async def test_link_saves_username(client):
    async with client as c:
        resp = await c.post("/api/leetcode/link", json={"username": "rock"})
        assert resp.status_code == 200
        assert resp.json()["success"] is True
        assert resp.json()["username"] == "rock"

        status = (await c.get("/api/leetcode/status")).json()
        assert status["enabled"] is True
        assert status["username"] == "rock"


@pytest.mark.asyncio
async def test_link_unknown_user_fails(client):
    async with client as c:
        resp = await c.post("/api/leetcode/link", json={"username": "missing"})
        assert resp.status_code == 200
        assert resp.json()["success"] is False
        assert "not found" in resp.json()["message"].lower()


@pytest.mark.asyncio
async def test_profile_returns_snapshot_and_analysis(client):
    async with client as c:
        await c.post("/api/leetcode/link", json={"username": "rock"})
        resp = await c.get("/api/leetcode/profile")
        assert resp.status_code == 200
        data = resp.json()
        assert data["linked"] is True
        assert data["username"] == "rock"
        assert data["profile"]["accepted"]["total"] == 16
        assert data["analysis"]["total_solved"] == 2
        assert len(data["recent_ac"]) == 2


@pytest.mark.asyncio
async def test_profile_not_linked(client):
    async with client as c:
        resp = await c.get("/api/leetcode/profile")
        data = resp.json()
        assert data["linked"] is False
        assert "Settings" in data["error"]


@pytest.mark.asyncio
async def test_recommendations(client):
    async with client as c:
        await c.post("/api/leetcode/link", json={"username": "rock"})
        resp = await c.get("/api/leetcode/recommendations", params={"count": 3})
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["username"] == "rock"
        assert 0 < len(data["recommendations"]) <= 3
        slugs = {r["title_slug"] for r in data["recommendations"]}
        assert "two-sum" not in slugs
        assert "valid-parentheses" not in slugs


@pytest.mark.asyncio
async def test_unlink_clears_username(client):
    async with client as c:
        await c.post("/api/leetcode/link", json={"username": "rock"})
        resp = await c.delete("/api/leetcode/link")
        assert resp.json()["enabled"] is False
        assert (await c.get("/api/leetcode/status")).json()["username"] is None
