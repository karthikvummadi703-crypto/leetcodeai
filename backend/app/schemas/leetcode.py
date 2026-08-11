"""
Pydantic schemas for the LeetCode account integration.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class LeetCodeLinkRequest(BaseModel):
    """Store the user's LeetCode username."""
    username: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="LeetCode username (public profile)",
    )


class LeetCodeLinkResponse(BaseModel):
    success: bool = True
    username: str
    message: str = "LeetCode account linked."


class LeetCodeProfileSummary(BaseModel):
    """Public profile + solved counts."""
    username: str
    real_name: str | None = None
    avatar: str | None = None
    ranking: int | None = None
    reputation: int | None = None
    country: str | None = None
    school: str | None = None
    accepted: dict[str, int] = Field(default_factory=dict)


class LeetCodeAccountResponse(BaseModel):
    success: bool = True
    linked: bool
    username: str | None = None
    profile: LeetCodeProfileSummary | None = None
    progress: dict[str, Any] | None = None
    recent_ac: list[dict[str, Any]] | None = None
    languages: list[dict[str, Any]] | None = None
    contest: dict[str, Any] | None = None
    analysis: dict[str, Any] | None = None
    error: str | None = None


class RecommendationItem(BaseModel):
    number: int
    title: str
    title_slug: str
    difficulty: str
    acceptance: float | None = None
    paid_only: bool = False
    has_solution: bool = True
    topics: list[str] = Field(default_factory=list)
    url: str = ""


class RecommendationsResponse(BaseModel):
    success: bool = True
    username: str
    message: str = ""
    solved_count: int = 0
    by_difficulty: dict[str, int] = Field(default_factory=dict)
    recommendations: list[RecommendationItem] = Field(default_factory=list)


class LeetCodeStatusResponse(BaseModel):
    success: bool = True
    enabled: bool
    username: str | None = None
