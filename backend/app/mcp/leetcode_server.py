"""
LeetCode MCP server.

Exposes the user's public LeetCode account as Model Context Protocol tools so
any MCP-capable client (Claude Desktop, Cursor, VS Code, opencode, ...) can:

* inspect a LeetCode profile and solved-problem history,
* analyse strengths / weaknesses,
* get personalised "solve this next" recommendations,
* look up any problem in the full local catalog (4018 problems) or generate
  a solution for a problem the user asks about.

Run standalone with:
    python -m app.mcp.leetcode_server           # stdio transport
    python -m app.mcp.leetcode_server --sse     # SSE transport
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from app.core import get_logger
from app.leetcode.client import (
    LeetCodeError,
    UserNotFoundError,
    get_leetcode_client,
)
from app.problems import get_catalog, recommend_next

log = get_logger("mcp.leetcode")

SERVER_NAME = "leetcode-guidance"
SERVER_VERSION = "1.0.0"

# Difficulty ladder used by the recommendation helper.
_DIFFICULTIES = ("Easy", "Medium", "Hard")


def _problem_payload(problem: dict[str, Any]) -> str:
    """Render a catalog problem dict into a compact markdown block."""
    topics = ", ".join(problem.get("topics") or []) or "—"
    acceptance = problem.get("acceptance")
    acceptance_text = f"{acceptance * 100:.1f}%" if acceptance is not None else "—"
    return (
        f"### {problem['number']}. {problem['title']} ({problem['difficulty']})\n"
        f"- URL: {problem.get('url', '')}\n"
        f"- Topics: {topics}\n"
        f"- Acceptance: {acceptance_text}\n"
        f"- Premium: {'yes' if problem.get('paid_only') else 'no'}"
    )


def create_server() -> Any:
    """Build and return the configured FastMCP server instance."""
    # Import lazily so non-MCP environments (e.g. the bare FastAPI app
    # without the mcp package) do not need mcp installed.
    from mcp.server.fastmcp import FastMCP

    server = FastMCP(
        SERVER_NAME,
        instructions=(
            "LeetCode Guidance AI — connects to a user's public LeetCode "
            "account. Use these tools to fetch profile/solved-problem data, "
            "analyse a user's progress, recommend the next problems to solve, "
            "and look up problems in the full LeetCode catalog."
        ),
    )

    # ── Account / analysis tools ─────────────────────────────────

    def _clean_username(raw: str) -> str:
        """Normalise a bare username or full profile URL to a username."""
        from app.leetcode.links import extract_leetcode_username

        return extract_leetcode_username(raw)

    @server.tool()
    async def get_leetcode_profile(username: str) -> str:
        """Return a user's public LeetCode profile and global solved counts. Accepts a username or profile link."""
        username = _clean_username(username)
        try:
            profile = await get_leetcode_client().get_profile(username)
        except UserNotFoundError:
            return f"LeetCode user '{username}' was not found. Double-check the username."
        except LeetCodeError as exc:
            return f"Could not reach LeetCode: {exc}"
        accepted = profile["accepted"]
        total = profile["total_submissions"]["total"]
        return (
            f"## {profile.get('real_name') or profile['username']} (@{profile['username']})\n"
            f"- Global ranking: {profile.get('ranking', '—')}\n"
            f"- Country: {profile.get('country') or '—'}\n"
            f"- School: {profile.get('school') or '—'}\n"
            f"- Problems accepted: {accepted['total']} "
            f"(Easy {accepted['easy']} / Medium {accepted['medium']} / Hard {accepted['hard']})\n"
            f"- Total submissions: {total}"
        )

    @server.tool()
    async def get_solved_problems(username: str, limit: int = 20) -> str:
        """Return a user's most recent accepted LeetCode submissions. Accepts a username or profile link."""
        username = _clean_username(username)
        try:
            submissions = await get_leetcode_client().get_recent_ac_submissions(username, limit)
        except UserNotFoundError:
            return f"LeetCode user '{username}' was not found."
        except LeetCodeError as exc:
            return f"Could not reach LeetCode: {exc}"
        if not submissions:
            return f"@{username} has no recent accepted submissions."
        lines = [f"- {s['title']} — https://leetcode.com/problems/{s['title_slug']}/"]
        return f"## Recent accepted submissions for @{username}\n" + "\n".join(lines)

    @server.tool()
    async def analyze_leetcode_account(username: str) -> str:
        """Analyse a LeetCode account and summarise solved problems by difficulty, topic and language. Accepts a username or profile link."""
        username = _clean_username(username)
        try:
            snapshot = await get_leetcode_client().fetch_user_snapshot(username)
        except UserNotFoundError:
            return f"LeetCode user '{username}' was not found."
        except LeetCodeError as exc:
            return f"Could not reach LeetCode: {exc}"

        accepted = snapshot["accepted"]
        progress = snapshot.get("progress", {})
        languages = snapshot.get("languages") or []
        contest = snapshot.get("contest")

        lines = [
            f"## LeetCode analysis for @{username}",
            f"- Solved: {accepted['total']} "
            f"(Easy {accepted['easy']} / Medium {accepted['medium']} / Hard {accepted['hard']})",
        ]
        if contest:
            lines.append(
                f"- Contest rating: {contest['rating']} "
                f"(top {contest['top_percentage']}%, attended {contest['contests_attended']})"
            )
        if languages:
            top_lang = max(languages, key=lambda item: item["problems_solved"])
            lines.append(
                f"- Top language: {top_lang['language']} ({top_lang['problems_solved']} problems)"
            )
        recent = snapshot.get("recent_ac") or []
        if recent:
            lines.append(f"- Recently solved: {', '.join(s['title'] for s in recent[:8])}")
        return "\n".join(lines)

    # ── Recommendation tools ─────────────────────────────────────

    @server.tool()
    async def recommend_next_problems(
        username: str,
        count: int = 5,
        difficulty: str = "",
    ) -> str:
        """Recommend the next problems a user should solve, based on their solved history. Accepts a username or profile link."""
        username = _clean_username(username)
        if difficulty and difficulty.lower() not in {d.lower() for d in _DIFFICULTIES}:
            return f"Difficulty must be one of {', '.join(_DIFFICULTIES)} (or empty)."
        try:
            submissions = await get_leetcode_client().get_recent_ac_submissions(username, limit=50)
            progress = await get_leetcode_client().get_progress(username)
        except UserNotFoundError:
            return f"LeetCode user '{username}' was not found."
        except LeetCodeError as exc:
            return f"Could not reach LeetCode: {exc}"

        solved_slugs = [s["title_slug"] for s in submissions]
        solved_problems = []
        catalog = get_catalog()
        for slug in solved_slugs:
            problem = catalog.get_by_slug(slug)
            if problem:
                solved_problems.append(problem.to_dict())

        recommended = recommend_next(
            solved_slugs,
            solved_problems,
            count=max(1, min(count, 10)),
            difficulty=difficulty or None,
        )
        if not recommended:
            return f"No unsolved {difficulty or 'free'} problems found for @{username}."

        accepted = progress.get("accepted", {})
        header = (
            f"## Recommended next problems for @{username}\n"
            f"Solved so far: {accepted.get('total', 0)} "
            f"(Easy {accepted.get('easy', 0)} / Medium {accepted.get('medium', 0)} "
            f"/ Hard {accepted.get('hard', 0)})\n"
        )
        body = "\n\n".join(_problem_payload(p) for p in recommended)
        return header + "\n\n" + body

    # ── Catalog tools ────────────────────────────────────────────

    @server.tool()
    async def search_problems(query: str, limit: int = 10) -> str:
        """Search the full LeetCode problem catalog by number, title or topic."""
        from app.problems import search_problems as search

        results = search(query, limit=max(1, min(limit, 20)))
        if not results:
            return f"No problems found matching '{query}'."
        return "\n\n".join(_problem_payload(p) for p in results)

    @server.tool()
    async def get_problem_detail(identifier: str) -> str:
        """Return details for one problem by number, title slug or title."""
        catalog = get_catalog()
        problem = None
        identifier = identifier.strip()
        if identifier.isdigit():
            problem = catalog.get_by_number(int(identifier))
        if problem is None:
            problem = catalog.get_by_slug(identifier) or catalog.get_by_title(identifier)
        if problem is None:
            return f"Problem '{identifier}' was not found in the catalog."
        return _problem_payload(problem.to_dict())

    return server


async def _run_stdio(server: Any) -> None:
    # FastMCP >= 1.9 owns the stdio transport itself.
    await server.run_stdio_async()


async def _run_sse(server: Any) -> None:
    # FastMCP exposes the SSE transport at /sse (SSE endpoint) and
    # /messages/ (client->server POST endpoint).
    await server.run_sse_async()


def main() -> None:
    """Standalone entry point: `python -m app.mcp.leetcode_server [--sse]`."""
    import sys

    server = create_server()
    if "--sse" in sys.argv:
        asyncio.run(_run_sse(server))
    else:
        asyncio.run(_run_stdio(server))


if __name__ == "__main__":
    main()
