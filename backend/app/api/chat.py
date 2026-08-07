"""
Chat API endpoints.

POST /chat           — Send a message and get an AI response (streaming or non-streaming).
POST /new-chat       — Create a new conversation.
GET  /chat-history   — List all conversations for the current user.
GET  /chat/search    — Search conversations by title or message content.
GET  /chat/{id}      — Load a full conversation.
POST /chat/{id}/regenerate — Remove the last user/assistant turn before re-asking.
DELETE /chat/{id}    — Delete a conversation.
PATCH  /chat/{id}    — Rename a conversation.
"""

from __future__ import annotations

import orjson

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.auth import get_current_user
from app.schemas import (
    ChatRequest,
    ChatResponse,
    NewChatRequest,
    NewChatResponse,
    ChatHistoryResponse,
    DeleteChatResponse,
    RenameChatRequest,
    RenameChatResponse,
    ConversationDetailResponse,
    SearchChatsResponse,
    TruncateResponse,
    UserProfile,
    MessageRole,
)
from app.services.conversation_memory import (
    create_conversation,
    load_conversation,
    append_message,
    list_conversations,
    delete_conversation,
    rename_conversation,
    search_conversations,
    truncate_last_turn,
)
from app.agent import Agent
from app.core import get_logger
from app.core.rate_limit import enforce_rate_limit

log = get_logger("api.chat")

router = APIRouter(tags=["Chat"])

# Singleton agent instance — created once on first import.
_agent = Agent()


# ── POST /chat ────────────────────────────────────────────────

@router.post("/chat", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    user: UserProfile = Depends(enforce_rate_limit),
):
    """
    Send a user message and receive an AI response.

    If `stream=true` in the request body, this endpoint returns
    a `text/event-stream` response instead.
    """
    # Ensure conversation exists; load it.
    conv = load_conversation(user.uid, body.conversation_id)

    # Persist the user message.
    append_message(user.uid, body.conversation_id, MessageRole.USER, body.message)

    # Streaming path.
    if body.stream:
        async def event_generator():
            full_response = ""
            try:
                async for chunk in _agent.run_stream(conv, body.message):
                    full_response += chunk
                    # JSON-encode each chunk so multi-line tokens survive SSE.
                    payload = orjson.dumps({"chunk": chunk}).decode("utf-8")
                    yield f"data: {payload}\n\n"
                yield "data: [DONE]\n\n"
            finally:
                # Persist whatever streamed (even if the client cancelled).
                if full_response:
                    append_message(
                        user.uid,
                        body.conversation_id,
                        MessageRole.ASSISTANT,
                        full_response,
                    )

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    # Non-streaming path.
    result = await _agent.run(conv, body.message)
    assistant_msg = append_message(
        user.uid, body.conversation_id, MessageRole.ASSISTANT, result.content
    )

    return ChatResponse(
        conversation_id=body.conversation_id,
        message=assistant_msg,
    )


# ── POST /new-chat ────────────────────────────────────────────

@router.post("/new-chat", response_model=NewChatResponse)
async def new_chat(
    body: NewChatRequest,
    user: UserProfile = Depends(enforce_rate_limit),
):
    """Create a new empty conversation."""
    conv = create_conversation(user.uid, body.title)
    return NewChatResponse(conversation_id=conv.id, title=conv.title)


# ── GET /chat-history ─────────────────────────────────────────

@router.get("/chat-history", response_model=ChatHistoryResponse)
async def chat_history(user: UserProfile = Depends(get_current_user)):
    """List all conversations for the authenticated user."""
    items = list_conversations(user.uid)
    return ChatHistoryResponse(conversations=items)


# ── GET /chat/search ────────────────────────────────────────────
# Registered before /chat/{conversation_id} so the literal segment
# wins the route match.

@router.get("/chat/search", response_model=SearchChatsResponse)
async def search_chats(
    q: str = "",
    user: UserProfile = Depends(get_current_user),
):
    """Search conversations by title or message content (partial match)."""
    items = search_conversations(user.uid, q)
    return SearchChatsResponse(query=q, conversations=items)


# ── GET /chat/{id} ──────────────────────────────────────────────

@router.get("/chat/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    conversation_id: str,
    user: UserProfile = Depends(get_current_user),
):
    """Load a full conversation including all messages."""
    conv = load_conversation(user.uid, conversation_id)
    return ConversationDetailResponse(conversation=conv)


# ── POST /chat/{id}/regenerate ──────────────────────────────────

@router.post("/chat/{conversation_id}/regenerate", response_model=TruncateResponse)
async def regenerate_chat(
    conversation_id: str,
    user: UserProfile = Depends(get_current_user),
):
    """
    Remove the last user message and its assistant response so the same
    question can be asked again without duplicating history.
    """
    count = truncate_last_turn(user.uid, conversation_id)
    return TruncateResponse(message_count=count)


# ── DELETE /chat/{id} ─────────────────────────────────────────

@router.delete("/chat/{conversation_id}", response_model=DeleteChatResponse)
async def delete_chat(
    conversation_id: str,
    user: UserProfile = Depends(get_current_user),
):
    """Delete a conversation."""
    deleted_id = delete_conversation(user.uid, conversation_id)
    return DeleteChatResponse(deleted_id=deleted_id)


# ── PATCH /chat/{id} ──────────────────────────────────────────

@router.patch("/chat/{conversation_id}", response_model=RenameChatResponse)
async def rename_chat(
    conversation_id: str,
    body: RenameChatRequest,
    user: UserProfile = Depends(get_current_user),
):
    """Rename a conversation."""
    conv = rename_conversation(user.uid, conversation_id, body.title)
    return RenameChatResponse(conversation_id=conv.id, title=conv.title)
