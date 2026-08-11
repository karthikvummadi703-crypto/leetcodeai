"""
Async LeetCode GraphQL client.

Reads a user's *public* LeetCode data (profile, solved-problem counts,
recent accepted submissions, language usage and contest ranking) from
LeetCode's public GraphQL API. No credentials are required — the data is
the same that is visible on a public LeetCode profile.

All network failures and unknown users are surfaced as typed exceptions so
callers (HTTP endpoints, the MCP server and the agent) can degrade
gracefully instead of crashing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import httpx
import orjson

from app.core import get_logger

log = get_logger("leetcode.client")

LEETCODE_GRAPHQL_URL = "https://leetcode.com/graphql"
DEFAULT_TIMEOUT = 20.0


class LeetCodeError(Exception):
    """Base error for anything that goes wrong talking to LeetCode."""


class UserNotFoundError(LeetCodeError):
    """Raised when the requested username does not exist on LeetCode."""


class LeetCodeRateLimitError(LeetCodeError):
    """Raised when LeetCode throttles the request."""


# ─── Data models ───────────────────────────────────────────────────

@dataclass
class DifficultyBreakdown:
    easy: int = 0
    medium: int = 0
    hard: int = 0

    @classmethod
    def from_count_list(cls, items: list[dict[str, Any]]) -> "DifficultyBreakdown":
        counts = DifficultyBreakdown()
        for item in items or []:
            difficulty = (item.get("difficulty") or "").lower()
            count = int(item.get("count") or 0)
            if difficulty == "easy":
                counts.easy = count
            elif difficulty == "medium":
                counts.medium = count
            elif difficulty == "hard":
                counts.hard = count
        return counts

    @property
    def total(self) -> int:
        return self.easy + self.medium + self.hard

    def to_dict(self) -> dict[str, int]:
        return {"easy": self.easy, "medium": self.medium, "hard": self.hard, "total": self.total}


@dataclass
class UserProgress:
    accepted: DifficultyBreakdown = field(default_factory=DifficultyBreakdown)
    failed: DifficultyBreakdown = field(default_factory=DifficultyBreakdown)
    untouched: DifficultyBreakdown = field(default_factory=DifficultyBreakdown)


@dataclass
class RecentSubmission:
    id: str
    title: str
    title_slug: str
    timestamp: int

    @classmethod
    def from_raw(cls, raw: dict[str, Any]) -> "RecentSubmission":
        return cls(
            id=str(raw.get("id", "")),
            title=raw.get("title", ""),
            title_slug=raw.get("titleSlug", ""),
            timestamp=int(raw.get("timestamp") or 0),
        )


# ─── GraphQL queries ───────────────────────────────────────────────

_QUERY_PROFILE = """
query userPublicProfile($username: String!) {
  matchedUser(username: $username) {
    username
    profile {
      realName
      userAvatar
      ranking
      reputation
      countryName
      school
    }
    submitStatsGlobal {
      acSubmissionNum { difficulty count }
      totalSubmissionNum { difficulty count }
    }
  }
}
"""

_QUERY_PROGRESS = """
query userProfileUserQuestionProgressV2($userSlug: String!) {
  userProfileUserQuestionProgressV2(userSlug: $userSlug) {
    numAcceptedQuestions { difficulty count }
    numFailedQuestions { difficulty count }
    numUntouchedQuestions { difficulty count }
  }
}
"""

_QUERY_RECENT_AC = """
query recentAcSubmissions($username: String!, $limit: Int!) {
  recentAcSubmissionList(username: $username, limit: $limit) {
    id
    title
    titleSlug
    timestamp
  }
}
"""

_QUERY_LANGUAGE = """
query languageStats($username: String!) {
  matchedUser(username: $username) {
    languageProblemCount {
      languageName
      problemsSolved
    }
  }
}
"""

_QUERY_CONTEST = """
query userContestRankingInfo($username: String!) {
  userContestRanking(username: $username) {
    attendedContestsCount
    rating
    globalRanking
    totalParticipants
    topPercentage
  }
}
"""


# ─── Client ────────────────────────────────────────────────────────

class LeetCodeClient:
    """Thin async wrapper around LeetCode's public GraphQL endpoint."""

    def __init__(self, base_url: str = LEETCODE_GRAPHQL_URL, timeout: float = DEFAULT_TIMEOUT) -> None:
        self._base_url = base_url
        self._timeout = timeout

    # ── low-level ────────────────────────────────────────────────

    async def _query(self, query: str, variables: dict[str, Any]) -> dict[str, Any]:
        """Run a GraphQL query and return the ``data`` payload."""
        try:
            async with httpx.AsyncClient(timeout=self._timeout, follow_redirects=True) as client:
                response = await client.post(
                    self._base_url,
                    json={"query": query, "variables": variables},
                    headers={"Content-Type": "application/json"},
                )
        except httpx.TimeoutException as exc:
            log.warning("LeetCode request timed out: {exc}", exc=exc)
            raise LeetCodeError("LeetCode request timed out.") from exc
        except httpx.HTTPError as exc:
            log.warning("LeetCode request failed: {exc}", exc=exc)
            raise LeetCodeError(f"LeetCode request failed: {exc}") from exc

        if response.status_code == 429:
            raise LeetCodeRateLimitError("LeetCode is rate-limiting requests. Please try again later.")
        if response.status_code >= 500:
            raise LeetCodeError(f"LeetCode returned status {response.status_code}.")

        try:
            payload = orjson.loads(response.content)
        except orjson.JSONDecodeError as exc:
            raise LeetCodeError("LeetCode returned an invalid response.") from exc

        if payload.get("errors"):
            message = payload["errors"][0].get("message", "unknown error")
            if "does not exist" in message or "doesn't exist" in message:
                raise UserNotFoundError(variables.get("username") or variables.get("userSlug") or "user")
            log.warning("LeetCode GraphQL error: {message}", message=message)
            raise LeetCodeError(f"LeetCode GraphQL error: {message}")

        return payload.get("data", {})

    # ── public helpers ───────────────────────────────────────────

    async def get_profile(self, username: str) -> dict[str, Any]:
        """Return the user's public profile + global solved counts."""
        data = await self._query(_QUERY_PROFILE, {"username": username})
        matched = data.get("matchedUser") or {}
        if not matched:
            raise UserNotFoundError(username)

        profile = matched.get("profile") or {}
        submit_stats = matched.get("submitStatsGlobal") or {}
        accepted = DifficultyBreakdown.from_count_list(
            (submit_stats.get("acSubmissionNum") or [])[1:]
        )
        total_submissions = DifficultyBreakdown.from_count_list(
            (submit_stats.get("totalSubmissionNum") or [])[1:]
        )

        return {
            "username": matched.get("username") or username,
            "real_name": profile.get("realName"),
            "avatar": profile.get("userAvatar"),
            "ranking": profile.get("ranking"),
            "reputation": profile.get("reputation"),
            "country": profile.get("countryName"),
            "school": profile.get("school"),
            "accepted": accepted.to_dict(),
            "total_submissions": total_submissions.to_dict(),
        }

    async def get_progress(self, username: str) -> dict[str, Any]:
        """Return accepted / failed / untouched problem counts by difficulty."""
        data = await self._query(_QUERY_PROGRESS, {"userSlug": username})
        progress = data.get("userProfileUserQuestionProgressV2") or {}
        return {
            "accepted": DifficultyBreakdown.from_count_list(
                progress.get("numAcceptedQuestions") or []
            ).to_dict(),
            "failed": DifficultyBreakdown.from_count_list(
                progress.get("numFailedQuestions") or []
            ).to_dict(),
            "untouched": DifficultyBreakdown.from_count_list(
                progress.get("numUntouchedQuestions") or []
            ).to_dict(),
        }

    async def get_recent_ac_submissions(
        self, username: str, limit: int = 20
    ) -> list[dict[str, Any]]:
        """Return the most recent accepted submissions."""
        data = await self._query(
            _QUERY_RECENT_AC, {"username": username, "limit": min(max(limit, 1), 50)}
        )
        submissions = data.get("recentAcSubmissionList") or []
        return [
            {"id": s.get("id", ""), "title": s.get("title", ""),
             "title_slug": s.get("titleSlug", ""), "timestamp": int(s.get("timestamp") or 0)}
            for s in submissions
        ]

    async def get_language_stats(self, username: str) -> list[dict[str, Any]]:
        """Return how many problems the user solved per language."""
        data = await self._query(_QUERY_LANGUAGE, {"username": username})
        matched = data.get("matchedUser") or {}
        counts = matched.get("languageProblemCount") or []
        return [
            {"language": item.get("languageName"), "problems_solved": int(item.get("problemsSolved") or 0)}
            for item in counts
            if item.get("problemsSolved")
        ]

    async def get_contest_ranking(self, username: str) -> dict[str, Any] | None:
        """Return contest rating / ranking, or ``None`` when the user never competed."""
        data = await self._query(_QUERY_CONTEST, {"username": username})
        ranking = data.get("userContestRanking")
        if not ranking:
            return None
        return {
            "contests_attended": int(ranking.get("attendedContestsCount") or 0),
            "rating": ranking.get("rating"),
            "global_ranking": ranking.get("globalRanking"),
            "top_percentage": ranking.get("topPercentage"),
        }

    async def fetch_user_snapshot(self, username: str) -> dict[str, Any]:
        """
        Fetch everything we know about a user in one call.

        Returns a single JSON-serialisable dict with profile, progress,
        recent submissions, language usage and contest ranking.

        Results are cached briefly (TTL configurable via
        ``LEETCODE_CACHE_TTL_SECONDS``) so the AI agent and the dashboard do
        not hammer LeetCode's public API on every request.
        """
        snapshot = await get_cached_snapshot(username)
        if snapshot is not None:
            return snapshot

        profile = await self.get_profile(username)
        progress = await self.get_progress(username)
        recent = await self.get_recent_ac_submissions(username, limit=20)
        languages = await self.get_language_stats(username)
        contest = await self.get_contest_ranking(username)
        snapshot = {
            **profile,
            "progress": progress,
            "recent_ac": recent,
            "languages": languages,
            "contest": contest,
        }
        set_cached_snapshot(username, snapshot)
        return snapshot


# ─── Snapshot cache (TTL) ──────────────────────────────────────────

import time as _time  # noqa: E402  (imported after class for clarity)

_snapshot_cache: dict[str, tuple[float, dict[str, Any]]] = {}


def get_cached_snapshot(username: str) -> dict[str, Any] | None:
    """Return a cached snapshot for ``username`` when still fresh."""
    entry = _snapshot_cache.get(username)
    if entry is None:
        return None
    stored_at, snapshot = entry
    from app.config import get_settings

    ttl = get_settings().leetcode_cache_ttl_seconds
    if _time.monotonic() - stored_at > ttl:
        _snapshot_cache.pop(username, None)
        return None
    return snapshot


def set_cached_snapshot(username: str, snapshot: dict[str, Any]) -> None:
    """Store a snapshot for ``username`` with the configured TTL."""
    _snapshot_cache[username] = (_time.monotonic(), snapshot)


def invalidate_snapshot(username: str | None = None) -> None:
    """Clear the cache (for one user, or all users when ``username`` is None)."""
    if username is None:
        _snapshot_cache.clear()
    else:
        _snapshot_cache.pop(username, None)


# Module-level singleton for the whole process.
_client: LeetCodeClient | None = None


def get_leetcode_client() -> LeetCodeClient:
    """Return the shared LeetCode client instance."""
    global _client
    if _client is None:
        _client = LeetCodeClient()
    return _client
