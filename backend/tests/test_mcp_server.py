"""
Tests for the LeetCode MCP server tools.

All six tools (``get_leetcode_profile``, ``get_solved_problems``,
``analyze_leetcode_account``, ``recommend_next_problems``,
``search_problems``, ``get_problem_detail``) are exercised with a stubbed
``LeetCodeClient`` so the suite stays offline. The network-dependent tools
are covered for the happy path, user-not-found, network-error and
empty-result cases.
"""

import app.mcp.leetcode_server as server_module
import pytest
from app.leetcode.client import LeetCodeError, UserNotFoundError
from app.mcp.leetcode_server import create_server

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

SUBMISSIONS = [
    {"id": "1", "title": "Two Sum", "title_slug": "two-sum", "timestamp": 1700000000},
    {
        "id": "2",
        "title": "Valid Parentheses",
        "title_slug": "valid-parentheses",
        "timestamp": 1700000001,
    },
    {
        "id": "3",
        "title": "Reverse Linked List",
        "title_slug": "reverse-linked-list",
        "timestamp": 1700000002,
    },
    {
        "id": "4",
        "title": "Contains Duplicate",
        "title_slug": "contains-duplicate",
        "timestamp": 1700000003,
    },
    {
        "id": "5",
        "title": "Merge Two Sorted Lists",
        "title_slug": "merge-two-sorted-lists",
        "timestamp": 1700000004,
    },
]

PROGRESS = {
    "accepted": PROFILE["accepted"],
    "failed": {"easy": 1, "medium": 2, "hard": 0, "total": 3},
    "untouched": {"easy": 900, "medium": 2000, "hard": 950, "total": 3850},
}

SNAPSHOT = {
    **PROFILE,
    "progress": PROGRESS,
    "recent_ac": SUBMISSIONS,
    "languages": [{"language": "Python3", "problems_solved": 12}],
    "contest": {
        "contests_attended": 3,
        "rating": 1500,
        "global_ranking": 50000,
        "top_percentage": 10.0,
    },
}


class StubLeetCodeClient:
    """Offline stand-in for the async LeetCode client."""

    def __init__(
        self,
        submissions=None,
        profile=None,
        snapshot=None,
        progress=None,
        last_limit=None,
    ) -> None:
        self.submissions = list(submissions or SUBMISSIONS)
        self.profile = dict(profile or PROFILE)
        self.snapshot = dict(snapshot or SNAPSHOT)
        self.progress = dict(progress or PROGRESS)
        self.last_limit = last_limit

    def _reject_if_missing(self, username: str) -> None:
        if username == "missing":
            raise UserNotFoundError(username)
        if username == "down":
            raise LeetCodeError("network down")

    async def get_profile(self, username: str) -> dict:
        self._reject_if_missing(username)
        return dict(self.profile)

    async def get_progress(self, username: str) -> dict:
        self._reject_if_missing(username)
        return dict(self.progress)

    async def get_recent_ac_submissions(self, username: str, limit: int = 20) -> list:
        self.last_limit = limit
        self._reject_if_missing(username)
        return list(self.submissions)

    async def fetch_user_snapshot(self, username: str) -> dict:
        self._reject_if_missing(username)
        return dict(self.snapshot)


@pytest.fixture
def server_and_stub():
    """A fresh server instance with the LeetCode client stubbed."""
    original = server_module.get_leetcode_client
    server = create_server()
    stub = StubLeetCodeClient()
    server_module.get_leetcode_client = lambda: stub
    yield server, stub
    server_module.get_leetcode_client = original


def get_tool(server, name):
    """Resolve a registered tool's callable from the FastMCP tool manager."""
    return server._tool_manager.get_tool(name).fn


# ── get_leetcode_profile ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_leetcode_profile_happy_path(server_and_stub):
    server, _stub = server_and_stub
    out = await get_tool(server, "get_leetcode_profile")("rock")
    assert "@rock" in out
    assert "Rock Lee" in out
    assert "Global ranking: 7704" in out
    assert "Problems accepted: 16" in out
    assert "Easy 10" in out and "Medium 5" in out and "Hard 1" in out
    assert "Total submissions: 36" in out


@pytest.mark.asyncio
async def test_get_leetcode_profile_accepts_profile_url(server_and_stub):
    server, _stub = server_and_stub
    out = await get_tool(server, "get_leetcode_profile")("https://leetcode.com/u/rock/")
    assert "@rock" in out


@pytest.mark.asyncio
async def test_get_leetcode_profile_user_not_found(server_and_stub):
    server, _stub = server_and_stub
    out = await get_tool(server, "get_leetcode_profile")("missing")
    assert "was not found" in out


@pytest.mark.asyncio
async def test_get_leetcode_profile_network_error(server_and_stub):
    server, _stub = server_and_stub
    out = await get_tool(server, "get_leetcode_profile")("down")
    assert "Could not reach LeetCode" in out


# ── get_solved_problems ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_solved_problems_happy_path(server_and_stub):
    server, _stub = server_and_stub
    out = await get_tool(server, "get_solved_problems")("rock")
    assert "## Recent accepted submissions for @rock" in out
    assert "Two Sum" in out and "https://leetcode.com/problems/two-sum/" in out
    assert "Valid Parentheses" in out
    assert "Reverse Linked List" in out
    # Every submission is rendered.
    assert out.count("- ") == 5


@pytest.mark.asyncio
async def test_get_solved_problems_respects_limit(server_and_stub):
    server, stub = server_and_stub
    out = await get_tool(server, "get_solved_problems")("rock", limit=2)
    # The client received the requested limit…
    assert stub.last_limit == 2
    # …and the display is truncated to exactly `limit` entries.
    assert out.count("- ") == 2
    assert "Two Sum" in out and "Valid Parentheses" in out
    assert "Reverse Linked List" not in out


@pytest.mark.asyncio
async def test_get_solved_problems_empty_results(server_and_stub):
    server, stub = server_and_stub
    stub.submissions = []
    out = await get_tool(server, "get_solved_problems")("rock")
    assert "no recent accepted submissions" in out


@pytest.mark.asyncio
async def test_get_solved_problems_user_not_found(server_and_stub):
    server, _stub = server_and_stub
    out = await get_tool(server, "get_solved_problems")("missing")
    assert "was not found" in out


@pytest.mark.asyncio
async def test_get_solved_problems_network_error(server_and_stub):
    server, _stub = server_and_stub
    out = await get_tool(server, "get_solved_problems")("down")
    assert "Could not reach LeetCode" in out


# ── analyze_leetcode_account ─────────────────────────────────────


@pytest.mark.asyncio
async def test_analyze_leetcode_account_happy_path(server_and_stub):
    server, _stub = server_and_stub
    out = await get_tool(server, "analyze_leetcode_account")("rock")
    assert "## LeetCode analysis for @rock" in out
    assert "Solved: 16" in out
    assert "Contest rating: 1500" in out and "top 10.0%" in out
    assert "Top language: Python3 (12 problems)" in out
    assert "Recently solved: Two Sum, Valid Parentheses, Reverse Linked List" in out


@pytest.mark.asyncio
async def test_analyze_leetcode_account_user_not_found(server_and_stub):
    server, _stub = server_and_stub
    out = await get_tool(server, "analyze_leetcode_account")("missing")
    assert "was not found" in out


@pytest.mark.asyncio
async def test_analyze_leetcode_account_network_error(server_and_stub):
    server, _stub = server_and_stub
    out = await get_tool(server, "analyze_leetcode_account")("down")
    assert "Could not reach LeetCode" in out


@pytest.mark.asyncio
async def test_analyze_leetcode_account_empty_extra_data(server_and_stub):
    server, stub = server_and_stub
    stub.snapshot = {**SNAPSHOT, "languages": [], "contest": None, "recent_ac": []}
    out = await get_tool(server, "analyze_leetcode_account")("rock")
    assert "## LeetCode analysis for @rock" in out
    assert "Solved: 16" in out
    assert "Contest rating" not in out
    assert "Top language" not in out


# ── recommend_next_problems ──────────────────────────────────────


@pytest.mark.asyncio
async def test_recommend_next_problems_happy_path(server_and_stub):
    server, _stub = server_and_stub
    out = await get_tool(server, "recommend_next_problems")("rock", count=3)
    assert "## Recommended next problems for @rock" in out
    assert "Solved so far: 16" in out
    # Solved problems must never be re-recommended.
    assert "Two Sum" not in out
    assert "Valid Parentheses" not in out
    assert out.count("### ") == 3


@pytest.mark.asyncio
async def test_recommend_next_problems_clamps_count(server_and_stub):
    server, _stub = server_and_stub
    out = await get_tool(server, "recommend_next_problems")("rock", count=100)
    assert out.count("### ") == 10


@pytest.mark.asyncio
async def test_recommend_next_problems_invalid_difficulty(server_and_stub):
    server, _stub = server_and_stub
    out = await get_tool(server, "recommend_next_problems")("rock", difficulty="nonsense")
    assert "Difficulty must be one of" in out


@pytest.mark.asyncio
async def test_recommend_next_problems_empty_solved_history(server_and_stub):
    server, stub = server_and_stub
    stub.submissions = []
    out = await get_tool(server, "recommend_next_problems")("rock", count=2)
    # A fresh account still gets sensible recommendations.
    assert "## Recommended next problems for @rock" in out
    assert out.count("### ") == 2


@pytest.mark.asyncio
async def test_recommend_next_problems_user_not_found(server_and_stub):
    server, _stub = server_and_stub
    out = await get_tool(server, "recommend_next_problems")("missing")
    assert "was not found" in out


@pytest.mark.asyncio
async def test_recommend_next_problems_network_error(server_and_stub):
    server, _stub = server_and_stub
    out = await get_tool(server, "recommend_next_problems")("down")
    assert "Could not reach LeetCode" in out


# ── search_problems ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_search_problems_happy_path(server_and_stub):
    server, _stub = server_and_stub
    out = await get_tool(server, "search_problems")("two sum", limit=3)
    assert "### 1. Two Sum" in out
    assert "Topics: Array, Hash Table" in out
    assert out.count("### ") <= 3


@pytest.mark.asyncio
async def test_search_problems_returns_no_results(server_and_stub):
    server, _stub = server_and_stub
    out = await get_tool(server, "search_problems")("zzzzzznotaword")
    assert "No problems found matching" in out


@pytest.mark.asyncio
async def test_search_problems_clamps_limit(server_and_stub):
    server, _stub = server_and_stub
    out = await get_tool(server, "search_problems")("sum", limit=500)
    assert out.count("### ") <= 20


# ── get_problem_detail ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_problem_detail_by_number(server_and_stub):
    server, _stub = server_and_stub
    out = await get_tool(server, "get_problem_detail")("1")
    assert "### 1. Two Sum (Easy)" in out
    assert "https://leetcode.com/problems/two-sum/" in out


@pytest.mark.asyncio
async def test_get_problem_detail_by_slug(server_and_stub):
    server, _stub = server_and_stub
    out = await get_tool(server, "get_problem_detail")("two-sum")
    assert "### 1. Two Sum (Easy)" in out


@pytest.mark.asyncio
async def test_get_problem_detail_renders_acceptance_as_percentage(server_and_stub):
    server, _stub = server_and_stub
    out = await get_tool(server, "get_problem_detail")("1")
    assert "Acceptance:" in out
    assert "%" in out
    # Acceptance must be a sane 0..100 value, never 57xx%.
    import re

    matches = re.findall(r"Acceptance: ([\d.]+)%", out)
    assert matches and all(0 <= float(m) <= 100 for m in matches)


@pytest.mark.asyncio
async def test_get_problem_detail_not_found(server_and_stub):
    server, _stub = server_and_stub
    out = await get_tool(server, "get_problem_detail")("zzzzqqqq")
    assert "was not found in the catalog" in out
