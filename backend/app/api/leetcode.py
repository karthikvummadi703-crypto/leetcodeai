"""
LeetCode account integration endpoints.

POST /api/leetcode/link             — Validate + store the user's LeetCode username.
GET  /api/leetcode/profile          — Fetch the linked account's profile + analysis.
GET  /api/leetcode/recommendations  — Recommend next problems to solve.
DELETE /api/leetcode/link           — Unlink the LeetCode account.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.auth import get_current_user
from app.core import get_logger
from app.leetcode.client import (
    LeetCodeError,
    UserNotFoundError,
    get_leetcode_client,
)
from app.problems import recommend_next
from app.problems.catalog import get_catalog
from app.schemas import (
    LeetCodeAccountResponse,
    LeetCodeLinkRequest,
    LeetCodeLinkResponse,
    LeetCodeProfileSummary,
    LeetCodeStatusResponse,
    RecommendationItem,
    RecommendationsResponse,
    UserProfile,
)
from app.services.conversation_memory import (
    clear_leetcode_username,
    get_leetcode_username,
    set_leetcode_username,
)

log = get_logger("api.leetcode")

router = APIRouter(prefix="/leetcode", tags=["LeetCode"])

_client = get_leetcode_client()


@router.get("/status", response_model=LeetCodeStatusResponse)
async def leetcode_status(user: UserProfile = Depends(get_current_user)):
    """Return whether a LeetCode account is linked to this user."""
    username = get_leetcode_username(user.uid)
    return LeetCodeStatusResponse(enabled=username is not None, username=username)


@router.post("/link", response_model=LeetCodeLinkResponse)
async def leetcode_link(
    body: LeetCodeLinkRequest,
    user: UserProfile = Depends(get_current_user),
):
    """Validate a LeetCode username and persist the link for this user."""
    username = body.username.strip()
    try:
        profile = await _client.get_profile(username)
    except UserNotFoundError:
        return LeetCodeLinkResponse(
            success=False,
            username=username,
            message=f"LeetCode user '{username}' was not found. Check the spelling and try again.",
        )
    except LeetCodeError as exc:
        return LeetCodeLinkResponse(
            success=False,
            username=username,
            message=f"Could not reach LeetCode: {exc}",
        )

    set_leetcode_username(user.uid, profile["username"])
    log.info(
        "Linked LeetCode account '{username}' for user {uid}",
        username=profile["username"],
        uid=user.uid,
    )
    return LeetCodeLinkResponse(
        success=True,
        username=profile["username"],
        message=f"Linked {profile['username']}. Your profile and progress are now available.",
    )


@router.delete("/link", response_model=LeetCodeStatusResponse)
async def leetcode_unlink(user: UserProfile = Depends(get_current_user)):
    """Remove the linked LeetCode account."""
    clear_leetcode_username(user.uid)
    return LeetCodeStatusResponse(enabled=False, username=None)


@router.get("/profile", response_model=LeetCodeAccountResponse)
async def leetcode_profile(user: UserProfile = Depends(get_current_user)):
    """Fetch the linked account's profile, progress and analysis."""
    username = get_leetcode_username(user.uid)
    if not username:
        return LeetCodeAccountResponse(
            linked=False,
            error="No LeetCode account linked. Link one from the Settings page.",
        )
    try:
        snapshot = await _client.fetch_user_snapshot(username)
    except UserNotFoundError:
        clear_leetcode_username(user.uid)
        return LeetCodeAccountResponse(
            linked=False,
            username=username,
            error="Linked LeetCode account no longer exists. Please re-link.",
        )
    except LeetCodeError as exc:
        return LeetCodeAccountResponse(
            linked=True,
            username=username,
            error=f"Could not reach LeetCode right now: {exc}",
        )

    from app.problems import analyze_solved
    from app.problems.catalog import get_catalog

    solved_problems: list[dict] = []
    catalog = get_catalog()
    for submission in snapshot.get("recent_ac") or []:
        problem = catalog.get_by_slug(submission["title_slug"])
        if problem:
            solved_problems.append(problem.to_dict())
    analysis = analyze_solved(solved_problems)
    analysis["recent_count"] = len(snapshot.get("recent_ac") or [])

    return LeetCodeAccountResponse(
        linked=True,
        username=username,
        profile=LeetCodeProfileSummary(**{
            "username": snapshot["username"],
            "real_name": snapshot.get("real_name"),
            "avatar": snapshot.get("avatar"),
            "ranking": snapshot.get("ranking"),
            "reputation": snapshot.get("reputation"),
            "country": snapshot.get("country"),
            "school": snapshot.get("school"),
            "accepted": snapshot.get("accepted", {}),
        }),
        progress=snapshot.get("progress"),
        recent_ac=snapshot.get("recent_ac"),
        languages=snapshot.get("languages"),
        contest=snapshot.get("contest"),
        analysis=analysis,
    )


@router.get("/recommendations", response_model=RecommendationsResponse)
async def leetcode_recommendations(
    count: int = 5,
    difficulty: str = "",
    user: UserProfile = Depends(get_current_user),
):
    """Return personalised 'solve next' recommendations based on solved history."""
    count = max(1, min(count, 10))
    username = get_leetcode_username(user.uid)
    if not username:
        return RecommendationsResponse(
            success=False,
            username="",
            message="No LeetCode account linked. Link one from the Settings page.",
        )

    try:
        submissions = await _client.get_recent_ac_submissions(username, limit=50)
        progress = await _client.get_progress(username)
    except UserNotFoundError:
        return RecommendationsResponse(
            success=False,
            username=username,
            message="Linked LeetCode account no longer exists. Please re-link.",
        )
    except LeetCodeError as exc:
        return RecommendationsResponse(
            success=False,
            username=username,
            message=f"Could not reach LeetCode right now: {exc}",
        )

    solved_slugs = [s["title_slug"] for s in submissions]
    catalog = get_catalog()
    solved_problems = []
    for slug in solved_slugs:
        problem = catalog.get_by_slug(slug)
        if problem:
            solved_problems.append(problem.to_dict())

    recommended = recommend_next(
        solved_slugs,
        solved_problems,
        count=count,
        difficulty=difficulty or None,
    )
    accepted = progress.get("accepted", {})

    return RecommendationsResponse(
        success=True,
        username=username,
        solved_count=len(solved_slugs),
        by_difficulty=accepted,
        recommendations=[RecommendationItem(**item) for item in recommended],
    )
