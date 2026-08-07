"""
User profile & feedback endpoints.

GET    /profile         — Return the authenticated user's profile.
POST   /profile/sync    — Upsert profile (display name, photo, last login).
DELETE /profile/chats   — Delete all of the user's conversations.
GET    /profile/export  — Export the user's data as JSON.
POST   /feedback        — Persist feedback on an AI response.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.auth import get_current_user
from app.schemas import (
    UserProfile,
    ProfileResponse,
    FeedbackRequest,
    FeedbackResponse,
    DeleteAllResponse,
    ExportResponse,
)
from app.services.conversation_memory import (
    sync_profile as persist_profile,
    delete_all_conversations,
    export_user_data,
    save_feedback,
)
from app.core import get_logger

log = get_logger("api.user")

router = APIRouter(tags=["User"])


@router.get("/profile", response_model=ProfileResponse)
async def profile(user: UserProfile = Depends(get_current_user)):
    """Return the profile of the currently authenticated user."""
    return ProfileResponse(user=user)


@router.post("/profile/sync", response_model=ProfileResponse)
async def sync_profile(user: UserProfile = Depends(get_current_user)):
    """Persist the user's profile and refresh their last-login time."""
    persisted = persist_profile(user)
    return ProfileResponse(user=persisted)


@router.delete("/profile/chats", response_model=DeleteAllResponse)
async def delete_all_chats(user: UserProfile = Depends(get_current_user)):
    """Permanently delete every conversation belonging to the user."""
    count = delete_all_conversations(user.uid)
    return DeleteAllResponse(deleted_count=count)


@router.get("/profile/export", response_model=ExportResponse)
async def export_profile(user: UserProfile = Depends(get_current_user)):
    """Return all user data (profile + conversations) as JSON."""
    payload = export_user_data(user)
    return ExportResponse(user=payload["user"], conversations=payload["conversations"])


@router.post("/feedback", response_model=FeedbackResponse)
async def feedback(
    body: FeedbackRequest,
    user: UserProfile = Depends(get_current_user),
):
    """Persist user feedback on an AI response."""
    save_feedback(
        user.uid,
        body.conversation_id,
        body.message_id,
        body.rating,
        body.comment,
    )
    return FeedbackResponse()
