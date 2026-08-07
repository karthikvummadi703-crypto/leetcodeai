"""
Unit tests for the conversation memory service.
"""

from app.services.conversation_memory import (
    create_conversation,
    load_conversation,
    append_message,
    list_conversations,
    delete_conversation,
    rename_conversation,
    generate_title,
    search_conversations,
    truncate_last_turn,
    delete_all_conversations,
    sync_profile,
    save_feedback,
)
from app.schemas import MessageRole, UserProfile
from app.core import NotFoundError

import pytest


def test_create_and_load():
    conv = create_conversation("test_user_1", "My Chat")
    loaded = load_conversation("test_user_1", conv.id)
    assert loaded.id == conv.id
    assert loaded.title == "My Chat"
    assert loaded.messages == []


def test_append_message():
    conv = create_conversation("test_user_2", "Append Test")
    msg = append_message("test_user_2", conv.id, MessageRole.USER, "Hello!")
    assert msg.role == MessageRole.USER
    assert msg.content == "Hello!"

    loaded = load_conversation("test_user_2", conv.id)
    assert len(loaded.messages) == 1


def test_list_conversations():
    uid = "test_user_3"
    create_conversation(uid, "A")
    create_conversation(uid, "B")
    items = list_conversations(uid)
    assert len(items) >= 2


def test_delete_conversation():
    uid = "test_user_4"
    conv = create_conversation(uid, "Delete Me")
    delete_conversation(uid, conv.id)
    with pytest.raises(NotFoundError):
        load_conversation(uid, conv.id)


def test_rename_conversation():
    uid = "test_user_5"
    conv = create_conversation(uid, "Old Title")
    rename_conversation(uid, conv.id, "New Title")
    loaded = load_conversation(uid, conv.id)
    assert loaded.title == "New Title"


def test_load_nonexistent_raises():
    with pytest.raises(NotFoundError):
        load_conversation("ghost_user", "nonexistent_id")


# ── Title generation ────────────────────────────────────────────

def test_generate_title_short_message():
    assert generate_title("Hello!") == "Hello!"


def test_generate_title_truncates_to_40_chars():
    long = "Can you explain the sliding window pattern and when it should be used"
    title = generate_title(long)
    assert len(title) <= 40


def test_generate_title_empty_message():
    assert generate_title("   \n  ") == "New Chat"


def test_first_user_message_autotitles_new_chat():
    uid = "autotitle_user"
    conv = create_conversation(uid, "New Chat")
    append_message(uid, conv.id, MessageRole.USER, "Explain binary search please")
    loaded = load_conversation(uid, conv.id)
    assert loaded.title != "New Chat"
    assert "binary search" in loaded.title.lower()


# ── Search ──────────────────────────────────────────────────────

def test_search_matches_title():
    uid = "search_user_1"
    conv = create_conversation(uid, "Two Sum Approach")
    append_message(uid, conv.id, MessageRole.USER, "hello")
    results = search_conversations(uid, "two sum")
    assert [r.id for r in results] == [conv.id]


def test_search_matches_message_content():
    uid = "search_user_2"
    conv = create_conversation(uid, "Untitled")
    append_message(uid, conv.id, MessageRole.USER, "Tell me about Dijkstra's algorithm")
    results = search_conversations(uid, "dijkstra")
    assert [r.id for r in results] == [conv.id]


def test_search_no_match_returns_empty():
    uid = "search_user_3"
    create_conversation(uid, "Only Title")
    assert search_conversations(uid, "zzzz-nothing") == []


# ── Regenerate (truncate last turn) ─────────────────────────────

def test_truncate_last_turn_removes_pair():
    uid = "truncate_user"
    conv = create_conversation(uid, "Truncate")
    append_message(uid, conv.id, MessageRole.USER, "q1")
    append_message(uid, conv.id, MessageRole.ASSISTANT, "a1")
    append_message(uid, conv.id, MessageRole.USER, "q2")
    append_message(uid, conv.id, MessageRole.ASSISTANT, "a2")

    count = truncate_last_turn(uid, conv.id)
    loaded = load_conversation(uid, conv.id)

    assert count == 2
    assert [m.content for m in loaded.messages] == ["q1", "a1"]


# ── Delete all + profile + feedback ─────────────────────────────

def test_delete_all_conversations():
    uid = "delete_all_user"
    create_conversation(uid, "A")
    create_conversation(uid, "B")
    assert delete_all_conversations(uid) == 2
    assert list_conversations(uid) == []


def test_sync_profile_persists():
    profile = sync_profile(UserProfile(uid="p_user", email="p@t.com", display_name="Pat"))
    assert profile.uid == "p_user"
    assert profile.display_name == "Pat"


def test_save_feedback_returns_id():
    feedback_id = save_feedback("f_user", "conv-1", "msg-1", 5, "Great!")
    assert isinstance(feedback_id, str)
    assert len(feedback_id) > 0
