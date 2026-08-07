"""
Pydantic schemas for the chat domain.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ──────────────────────────────────────────────
# Enums
# ──────────────────────────────────────────────

class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


# ──────────────────────────────────────────────
# Request schemas
# ──────────────────────────────────────────────

class ChatRequest(BaseModel):
    """Payload sent by the frontend to request an AI response."""
    conversation_id: str = Field(..., min_length=1, description="Unique conversation identifier")
    message: str = Field(..., min_length=1, max_length=10_000, description="User message text")
    stream: bool = Field(default=True, description="Whether to stream the response")


class NewChatRequest(BaseModel):
    """Create a new conversation."""
    title: str = Field(default="New Chat", max_length=200)


class RenameChatRequest(BaseModel):
    """Rename an existing conversation."""
    title: str = Field(..., min_length=1, max_length=200)


class FeedbackRequest(BaseModel):
    """User feedback on an AI response."""
    conversation_id: str = Field(..., min_length=1)
    message_id: str = Field(..., min_length=1)
    rating: int = Field(..., ge=1, le=5, description="1–5 star rating")
    comment: str = Field(default="", max_length=2000)


# ──────────────────────────────────────────────
# Domain models
# ──────────────────────────────────────────────

class Message(BaseModel):
    """A single message within a conversation."""
    id: str = Field(..., description="Unique message ID")
    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=_utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)


class Conversation(BaseModel):
    """A full conversation thread."""
    id: str
    user_id: str
    title: str = "New Chat"
    messages: list[Message] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


class UserProfile(BaseModel):
    """Public-facing user profile."""
    uid: str
    email: str | None = None
    display_name: str | None = None
    photo_url: str | None = None


# ──────────────────────────────────────────────
# Response schemas
# ──────────────────────────────────────────────

class ChatResponse(BaseModel):
    """Non-streaming AI response."""
    success: bool = True
    conversation_id: str
    message: Message


class NewChatResponse(BaseModel):
    success: bool = True
    conversation_id: str
    title: str


class ConversationListItem(BaseModel):
    id: str
    title: str
    updated_at: datetime


class ChatHistoryResponse(BaseModel):
    success: bool = True
    conversations: list[ConversationListItem] = Field(default_factory=list)


class DeleteChatResponse(BaseModel):
    success: bool = True
    deleted_id: str


class RenameChatResponse(BaseModel):
    success: bool = True
    conversation_id: str
    title: str


class ConversationDetailResponse(BaseModel):
    """Full conversation with all messages."""
    success: bool = True
    conversation: Conversation


class SearchChatsResponse(BaseModel):
    """Results of a sidebar search across titles and message content."""
    success: bool = True
    query: str = ""
    conversations: list[ConversationListItem] = Field(default_factory=list)


class TruncateResponse(BaseModel):
    """Response after removing the last user/assistant turn (regenerate)."""
    success: bool = True
    message_count: int


class ExportedConversation(BaseModel):
    """A conversation in the portable export format."""
    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    messages: list[Message]


class DeleteAllResponse(BaseModel):
    success: bool = True
    deleted_count: int


class ExportResponse(BaseModel):
    success: bool = True
    exported_at: datetime = Field(default_factory=_utcnow)
    user: UserProfile
    conversations: list[ExportedConversation] = Field(default_factory=list)


class ProfileResponse(BaseModel):
    success: bool = True
    user: UserProfile


class FeedbackResponse(BaseModel):
    success: bool = True
    message: str = "Feedback received. Thank you!"


class HealthResponse(BaseModel):
    success: bool = True
    status: str = "healthy"
    environment: str = "development"
    version: str = "0.1.0"


class ErrorResponse(BaseModel):
    success: bool = False
    error: str
