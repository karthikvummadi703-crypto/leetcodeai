"""
Conversation persistence service.

Persists conversations, messages, user profiles, and feedback to Cloud
Firestore when Firebase credentials are configured. When they are not
(local development, tests), it transparently falls back to an in-memory
store so the app keeps working.

Every operation is scoped to the authenticated user's UID — the store
never reads or writes another user's data.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from app.core import ForbiddenError, NotFoundError, get_logger
from app.schemas import (
    Conversation,
    ConversationListItem,
    ExportedConversation,
    Message,
    MessageRole,
    UserProfile,
)

log = get_logger("conversation_memory")


def _utcnow() -> datetime:
    """Timezone-aware UTC now (Firestore requires aware datetimes)."""
    return datetime.now(UTC)


def generate_title(text: str, max_len: int = 40) -> str:
    """Derive a short chat title from a user message."""
    cleaned = " ".join(text.split())
    if not cleaned:
        return "New Chat"
    if len(cleaned) <= max_len:
        return cleaned
    cut = cleaned[:max_len]
    last_space = cut.rfind(" ")
    if last_space > max_len * 0.6:
        cut = cut[:last_space]
    title = cut.rstrip()
    return title.rstrip(".,;:!?") or cleaned[:max_len]


# ──────────────────────────────────────────────
# In-memory store (fallback for dev + tests)
# ──────────────────────────────────────────────


class InMemoryStore:
    """Keeps conversations in a dict keyed by user_id."""

    def __init__(self) -> None:
        self._store: dict[str, dict[str, Conversation]] = {}
        self._profiles: dict[str, dict[str, Any]] = {}
        self._feedback: list[dict[str, Any]] = []
        self._leetcode_links: dict[str, str] = {}

    def _user_store(self, user_id: str) -> dict[str, Conversation]:
        return self._store.setdefault(user_id, {})

    def create_conversation(self, user_id: str, title: str = "New Chat") -> Conversation:
        conv_id = str(uuid.uuid4())
        now = _utcnow()
        conv = Conversation(
            id=conv_id, user_id=user_id, title=title, messages=[], created_at=now, updated_at=now
        )
        self._user_store(user_id)[conv_id] = conv
        log.info("Created conversation {cid} for user {uid}", cid=conv_id, uid=user_id)
        return conv

    def load_conversation(self, user_id: str, conversation_id: str) -> Conversation:
        conv = self._user_store(user_id).get(conversation_id)
        if conv is None:
            raise NotFoundError(f"Conversation {conversation_id} not found.")
        return conv

    def append_message(
        self, user_id: str, conversation_id: str, role: MessageRole, content: str
    ) -> Message:
        conv = self.load_conversation(user_id, conversation_id)
        msg = Message(id=str(uuid.uuid4()), role=role, content=content, timestamp=_utcnow())
        conv.messages.append(msg)
        conv.updated_at = _utcnow()
        if (
            role == MessageRole.USER
            and conv.title in ("", "New Chat")
            and sum(1 for m in conv.messages if m.role == MessageRole.USER) == 1
        ):
            conv.title = generate_title(content)
        return msg

    def list_conversations(self, user_id: str) -> list[ConversationListItem]:
        items = [
            ConversationListItem(id=c.id, title=c.title, updated_at=c.updated_at)
            for c in self._user_store(user_id).values()
        ]
        items.sort(key=lambda x: x.updated_at, reverse=True)
        return items

    def delete_conversation(self, user_id: str, conversation_id: str) -> str:
        store = self._user_store(user_id)
        if conversation_id not in store:
            raise NotFoundError(f"Conversation {conversation_id} not found.")
        del store[conversation_id]
        log.info("Deleted conversation {cid} for user {uid}", cid=conversation_id, uid=user_id)
        return conversation_id

    def rename_conversation(self, user_id: str, conversation_id: str, title: str) -> Conversation:
        conv = self.load_conversation(user_id, conversation_id)
        conv.title = title
        conv.updated_at = _utcnow()
        log.info("Renamed conversation {cid} to '{title}'", cid=conversation_id, title=title)
        return conv

    def search_conversations(self, user_id: str, query: str) -> list[ConversationListItem]:
        q = query.strip().lower()
        items = self.list_conversations(user_id)
        if not q:
            return items
        results: list[ConversationListItem] = []
        for item in items:
            if q in item.title.lower():
                results.append(item)
                continue
            conv = self._user_store(user_id).get(item.id)
            if conv and any(q in m.content.lower() for m in conv.messages):
                results.append(item)
        return results

    def truncate_last_turn(self, user_id: str, conversation_id: str) -> int:
        """Drop the final user message and everything after it."""
        conv = self.load_conversation(user_id, conversation_id)
        last_user = next(
            (
                i
                for i in range(len(conv.messages) - 1, -1, -1)
                if conv.messages[i].role == MessageRole.USER
            ),
            None,
        )
        if last_user is not None:
            del conv.messages[last_user:]
        conv.updated_at = _utcnow()
        return len(conv.messages)

    def delete_all_conversations(self, user_id: str) -> int:
        store = self._user_store(user_id)
        count = len(store)
        store.clear()
        log.info("Deleted all {count} conversations for user {uid}", count=count, uid=user_id)
        return count

    def export_user_data(self, profile: UserProfile) -> dict[str, Any]:
        conversations = [
            ExportedConversation(
                id=c.id,
                title=c.title,
                created_at=c.created_at,
                updated_at=c.updated_at,
                messages=[Message(**m.model_dump()) for m in c.messages],
            )
            for c in sorted(
                self._user_store(profile.uid).values(), key=lambda c: c.updated_at, reverse=True
            )
        ]
        return {"user": profile, "conversations": conversations}

    def sync_profile(self, profile: UserProfile) -> UserProfile:
        self._profiles[profile.uid] = {
            "email": profile.email,
            "display_name": profile.display_name,
            "photo_url": profile.photo_url,
            "last_login": _utcnow(),
        }
        return profile

    def save_feedback(
        self,
        user_id: str,
        conversation_id: str,
        message_id: str,
        rating: int,
        comment: str,
    ) -> str:
        feedback_id = str(uuid.uuid4())
        self._feedback.append(
            {
                "id": feedback_id,
                "uid": user_id,
                "conversation_id": conversation_id,
                "message_id": message_id,
                "rating": rating,
                "comment": comment,
                "created_at": _utcnow(),
            }
        )
        log.info(
            "Feedback from {uid}: conv={cid} msg={mid} rating={r}",
            uid=user_id,
            cid=conversation_id,
            mid=message_id,
            r=rating,
        )
        return feedback_id

    # -- LeetCode account linking --------------------------------

    def set_leetcode_username(self, user_id: str, username: str) -> str:
        self._leetcode_links[user_id] = username.strip()
        log.info(
            "Linked LeetCode username '{username}' for user {uid}",
            username=username.strip(),
            uid=user_id,
        )
        return username.strip()

    def get_leetcode_username(self, user_id: str) -> str | None:
        return self._leetcode_links.get(user_id)

    def clear_leetcode_username(self, user_id: str) -> None:
        self._leetcode_links.pop(user_id, None)
        log.info("Unlinked LeetCode account for user {uid}", uid=user_id)


# ──────────────────────────────────────────────
# Firestore store (production)
# ──────────────────────────────────────────────


class FirestoreStore:
    """Persists conversations to Cloud Firestore, scoped by user UID."""

    def __init__(self) -> None:
        from firebase_admin import firestore as admin_firestore

        from app.auth.firebase_auth import get_firebase_app

        app = get_firebase_app()
        if app is None:
            raise RuntimeError("Firebase Admin is not initialised.")
        self._db = admin_firestore.client(app=app)

    # -- low-level helpers -----------------------------------------

    def _conv_ref(self, conversation_id: str):
        return self._db.collection("conversations").document(conversation_id)

    def _msg_coll(self, conversation_id: str):
        return self._conv_ref(conversation_id).collection("messages")

    def _check_owner(self, user_id: str, conversation_id: str) -> dict[str, Any]:
        """Ensure the conversation exists and belongs to the user."""
        doc = self._conv_ref(conversation_id).get()
        if not doc.exists:
            raise NotFoundError(f"Conversation {conversation_id} not found.")
        data = doc.to_dict() or {}
        if data.get("uid") != user_id:
            raise ForbiddenError("You do not have access to this conversation.")
        return data

    def _messages_sorted(self, conversation_id: str) -> list[Message]:
        messages: list[Message] = []
        for doc in self._msg_coll(conversation_id).order_by("timestamp").stream():
            data = doc.to_dict() or {}
            messages.append(
                Message(
                    id=doc.id,
                    role=data.get("role", MessageRole.USER.value),
                    content=data.get("content", ""),
                    timestamp=data.get("timestamp", _utcnow()),
                    metadata=data.get("metadata", {}),
                )
            )
        return messages

    # -- public interface ------------------------------------------

    def create_conversation(self, user_id: str, title: str = "New Chat") -> Conversation:
        conv_id = str(uuid.uuid4())
        now = _utcnow()
        self._conv_ref(conv_id).set(
            {"uid": user_id, "title": title, "created_at": now, "updated_at": now}
        )
        log.info("Created conversation {cid} for user {uid}", cid=conv_id, uid=user_id)
        return Conversation(
            id=conv_id, user_id=user_id, title=title, messages=[], created_at=now, updated_at=now
        )

    def load_conversation(self, user_id: str, conversation_id: str) -> Conversation:
        data = self._check_owner(user_id, conversation_id)
        return Conversation(
            id=conversation_id,
            user_id=user_id,
            title=data.get("title", "New Chat"),
            messages=self._messages_sorted(conversation_id),
            created_at=data.get("created_at", _utcnow()),
            updated_at=data.get("updated_at", _utcnow()),
        )

    def append_message(
        self, user_id: str, conversation_id: str, role: MessageRole, content: str
    ) -> Message:
        self._check_owner(user_id, conversation_id)
        msg_id = str(uuid.uuid4())
        now = _utcnow()
        self._msg_coll(conversation_id).document(msg_id).set(
            {"role": role.value, "content": content, "timestamp": now, "metadata": {}}
        )
        update: dict[str, Any] = {"updated_at": now}
        if role == MessageRole.USER:
            msgs = self._messages_sorted(conversation_id)
            first_user = sum(1 for m in msgs if m.role == MessageRole.USER) == 1
            doc = self._conv_ref(conversation_id).get()
            data = doc.to_dict() or {}
            if first_user and data.get("title", "New Chat") in ("", "New Chat"):
                update["title"] = generate_title(content)
        self._conv_ref(conversation_id).update(update)
        return Message(id=msg_id, role=role, content=content, timestamp=now)

    def list_conversations(self, user_id: str) -> list[ConversationListItem]:
        items: list[ConversationListItem] = []
        snap = self._db.collection("conversations").where("uid", "==", user_id).limit(1000).stream()
        for doc in snap:
            data = doc.to_dict() or {}
            if "updated_at" not in data:
                continue
            items.append(
                ConversationListItem(
                    id=doc.id, title=data.get("title", "New Chat"), updated_at=data["updated_at"]
                )
            )
        items.sort(key=lambda x: x.updated_at, reverse=True)
        return items

    def delete_conversation(self, user_id: str, conversation_id: str) -> str:
        self._check_owner(user_id, conversation_id)
        for m in self._msg_coll(conversation_id).stream():
            m.reference.delete()
        self._conv_ref(conversation_id).delete()
        log.info("Deleted conversation {cid} for user {uid}", cid=conversation_id, uid=user_id)
        return conversation_id

    def rename_conversation(self, user_id: str, conversation_id: str, title: str) -> Conversation:
        self._check_owner(user_id, conversation_id)
        self._conv_ref(conversation_id).update({"title": title, "updated_at": _utcnow()})
        log.info("Renamed conversation {cid} to '{title}'", cid=conversation_id, title=title)
        return self.load_conversation(user_id, conversation_id)

    def search_conversations(self, user_id: str, query: str) -> list[ConversationListItem]:
        q = query.strip().lower()
        items = self.list_conversations(user_id)
        if not q:
            return items
        results: list[ConversationListItem] = []
        for item in items:
            if q in item.title.lower():
                results.append(item)
                continue
            snap = (
                self._msg_coll(item.id)
                .order_by("timestamp", direction="DESCENDING")
                .limit(100)
                .stream()
            )
            for doc in snap:
                if q in (doc.get("content") or "").lower():
                    results.append(item)
                    break
        return results

    def truncate_last_turn(self, user_id: str, conversation_id: str) -> int:
        self._check_owner(user_id, conversation_id)
        msgs = self._messages_sorted(conversation_id)
        last_user = next(
            (i for i in range(len(msgs) - 1, -1, -1) if msgs[i].role == MessageRole.USER),
            None,
        )
        if last_user is not None:
            for m in msgs[last_user:]:
                self._msg_coll(conversation_id).document(m.id).delete()
        self._conv_ref(conversation_id).update({"updated_at": _utcnow()})
        return last_user if last_user is not None else len(msgs)

    def delete_all_conversations(self, user_id: str) -> int:
        count = 0
        snap = self._db.collection("conversations").where("uid", "==", user_id).stream()
        for doc in snap:
            for m in self._msg_coll(doc.id).stream():
                m.reference.delete()
            doc.reference.delete()
            count += 1
        log.info("Deleted all {count} conversations for user {uid}", count=count, uid=user_id)
        return count

    def export_user_data(self, profile: UserProfile) -> dict[str, Any]:
        conversations: list[ExportedConversation] = []
        snap = self._db.collection("conversations").where("uid", "==", profile.uid).stream()
        for doc in snap:
            data = doc.to_dict() or {}
            messages = [
                Message(
                    id=m.id,
                    role=m.role,
                    content=m.content,
                    timestamp=m.timestamp,
                    metadata=m.metadata,
                )
                for m in self._messages_sorted(doc.id)
            ]
            conversations.append(
                ExportedConversation(
                    id=doc.id,
                    title=data.get("title", "New Chat"),
                    created_at=data.get("created_at", _utcnow()),
                    updated_at=data.get("updated_at", _utcnow()),
                    messages=messages,
                )
            )
        conversations.sort(key=lambda c: c.updated_at, reverse=True)
        return {"user": profile, "conversations": conversations}

    def sync_profile(self, profile: UserProfile) -> UserProfile:
        ref = self._db.collection("users").document(profile.uid)
        now = _utcnow()
        payload = {
            "display_name": profile.display_name,
            "email": profile.email,
            "photo_url": profile.photo_url,
        }
        if ref.get().exists:
            ref.update({**payload, "last_login": now})
        else:
            ref.set({**payload, "created_at": now, "last_login": now})
        return profile

    def save_feedback(
        self,
        user_id: str,
        conversation_id: str,
        message_id: str,
        rating: int,
        comment: str,
    ) -> str:
        feedback_id = str(uuid.uuid4())
        self._db.collection("feedback").document(feedback_id).set(
            {
                "uid": user_id,
                "conversation_id": conversation_id,
                "message_id": message_id,
                "rating": rating,
                "comment": comment,
                "created_at": _utcnow(),
            }
        )
        log.info(
            "Feedback from {uid}: conv={cid} msg={mid} rating={r}",
            uid=user_id,
            cid=conversation_id,
            mid=message_id,
            r=rating,
        )
        return feedback_id

    # -- LeetCode account linking --------------------------------

    def set_leetcode_username(self, user_id: str, username: str) -> str:
        username = username.strip()
        ref = self._db.collection("users").document(user_id)
        if ref.get().exists:
            ref.update({"leetcode_username": username})
        else:
            ref.set({"leetcode_username": username, "created_at": _utcnow()})
        log.info(
            "Linked LeetCode username '{username}' for user {uid}", username=username, uid=user_id
        )
        return username

    def get_leetcode_username(self, user_id: str) -> str | None:
        doc = self._db.collection("users").document(user_id).get()
        if not doc.exists:
            return None
        return doc.to_dict().get("leetcode_username")

    def clear_leetcode_username(self, user_id: str) -> None:
        ref = self._db.collection("users").document(user_id)
        if ref.get().exists:
            ref.update({"leetcode_username": None})
        log.info("Unlinked LeetCode account for user {uid}", uid=user_id)


# ──────────────────────────────────────────────
# Store selection
# ──────────────────────────────────────────────


def _build_store() -> InMemoryStore | FirestoreStore:
    import os

    from app.config import get_settings

    # Force the in-memory store (used by the test suite — never touch Firestore).
    if os.environ.get("MEMORY_STORE", "").lower() == "memory":
        log.info("Using in-memory conversation store (forced by MEMORY_STORE)")
        return InMemoryStore()

    settings = get_settings()
    if not settings.firebase_project_id:
        log.info("Firebase not configured — using in-memory conversation store")
        return InMemoryStore()

    from app.auth.firebase_auth import get_firebase_app

    app = get_firebase_app()
    if app is None:
        log.warning("Firebase initialisation failed — using in-memory conversation store")
        return InMemoryStore()

    try:
        store = FirestoreStore()
        log.info("Using Cloud Firestore conversation store")
        return store
    except Exception as exc:  # noqa: BLE001 - fall back to the in-memory store on any init failure
        log.error("Failed to initialise Firestore store: {exc}", exc=exc)
        return InMemoryStore()


_store: InMemoryStore | FirestoreStore = _build_store()


# ──────────────────────────────────────────────
# Module-level API (kept for backwards compatibility)
# ──────────────────────────────────────────────


def create_conversation(user_id: str, title: str = "New Chat") -> Conversation:
    return _store.create_conversation(user_id, title)


def load_conversation(user_id: str, conversation_id: str) -> Conversation:
    return _store.load_conversation(user_id, conversation_id)


def append_message(user_id: str, conversation_id: str, role: MessageRole, content: str) -> Message:
    return _store.append_message(user_id, conversation_id, role, content)


def list_conversations(user_id: str) -> list[ConversationListItem]:
    return _store.list_conversations(user_id)


def delete_conversation(user_id: str, conversation_id: str) -> str:
    return _store.delete_conversation(user_id, conversation_id)


def rename_conversation(user_id: str, conversation_id: str, title: str) -> Conversation:
    return _store.rename_conversation(user_id, conversation_id, title)


def search_conversations(user_id: str, query: str) -> list[ConversationListItem]:
    return _store.search_conversations(user_id, query)


def truncate_last_turn(user_id: str, conversation_id: str) -> int:
    return _store.truncate_last_turn(user_id, conversation_id)


def delete_all_conversations(user_id: str) -> int:
    return _store.delete_all_conversations(user_id)


def export_user_data(profile: UserProfile) -> dict[str, Any]:
    return _store.export_user_data(profile)


def sync_profile(profile: UserProfile) -> UserProfile:
    return _store.sync_profile(profile)


def save_feedback(
    user_id: str,
    conversation_id: str,
    message_id: str,
    rating: int,
    comment: str,
) -> str:
    return _store.save_feedback(user_id, conversation_id, message_id, rating, comment)


def set_leetcode_username(user_id: str, username: str) -> str:
    return _store.set_leetcode_username(user_id, username)


def get_leetcode_username(user_id: str) -> str | None:
    return _store.get_leetcode_username(user_id)


def clear_leetcode_username(user_id: str) -> None:
    _store.clear_leetcode_username(user_id)
