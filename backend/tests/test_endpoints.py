"""
End-to-end tests for the chat & user REST endpoints.

Auth is bypassed by overriding ``get_current_user`` so the full request
pipeline (routing → validation → service layer → response) is exercised
without touching Firebase. Conversations live in the in-memory store.
"""

import pytest
from app.auth import get_current_user
from app.schemas import UserProfile
from httpx import ASGITransport, AsyncClient
from main import app


@pytest.fixture
def client():
    async def fake_user() -> UserProfile:
        return UserProfile(uid="e2e-user", email="e2e@test.com")

    app.dependency_overrides[get_current_user] = fake_user
    transport = ASGITransport(app=app)
    yield AsyncClient(transport=transport, base_url="http://test")
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_new_chat_and_list(client):
    async with client as c:
        created = await c.post("/api/new-chat", json={"title": "E2E Chat"})
        assert created.status_code == 200
        conv_id = created.json()["conversation_id"]

        listed = await c.get("/api/chat-history")
        assert listed.status_code == 200
        ids = [x["id"] for x in listed.json()["conversations"]]
        assert conv_id in ids


@pytest.mark.asyncio
async def test_chat_non_streaming_persists_turn(client, monkeypatch):
    from app.api import chat as chat_module

    class StubAgent:
        def __init__(self):
            self.last_message = None

        async def run(self, conversation, user_message):
            self.last_message = user_message
            return type("R", (), {"content": "Great question!"})()

        async def run_stream(self, conversation, user_message):
            yield "Great question!"

    stub = StubAgent()
    monkeypatch.setattr(chat_module, "_agent", stub)

    async with client as c:
        conv = (await c.post("/api/new-chat", json={"title": "T"})).json()["conversation_id"]
        resp = await c.post(
            "/api/chat",
            json={"conversation_id": conv, "message": "Explain binary search", "stream": False},
        )
        assert resp.status_code == 200
        assert resp.json()["message"]["role"] == "assistant"
        assert stub.last_message == "Explain binary search"

        detail = (await c.get(f"/api/chat/{conv}")).json()["conversation"]
        roles = [m["role"] for m in detail["messages"]]
        assert roles == ["user", "assistant"]


@pytest.mark.asyncio
async def test_chat_search(client):
    async with client as c:
        conv = (await c.post("/api/new-chat", json={"title": "Merge Sort Deep Dive"})).json()[
            "conversation_id"
        ]
        await c.post(
            "/api/chat",
            json={"conversation_id": conv, "message": "Tell me about merge sort", "stream": False},
        )

        found = (await c.get("/api/chat/search", params={"q": "merge sort"})).json()
        assert [x["id"] for x in found["conversations"]] == [conv]


@pytest.mark.asyncio
async def test_rename_and_delete_chat(client):
    async with client as c:
        conv = (await c.post("/api/new-chat", json={"title": "Old"})).json()["conversation_id"]

        renamed = await c.patch(f"/api/chat/{conv}", json={"title": "New Name"})
        assert renamed.status_code == 200
        assert renamed.json()["title"] == "New Name"

        deleted = await c.delete(f"/api/chat/{conv}")
        assert deleted.status_code == 200
        assert deleted.json()["deleted_id"] == conv

        detail = await c.get(f"/api/chat/{conv}")
        assert detail.status_code == 404


@pytest.mark.asyncio
async def test_regenerate_truncates_last_turn(client):
    from app.api import chat as chat_module

    class StubAgent:
        async def run(self, conversation, user_message):
            return type("R", (), {"content": "answer"})()

        async def run_stream(self, conversation, user_message):
            yield "answer"

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(chat_module, "_agent", StubAgent())

    async with client as c:
        conv = (await c.post("/api/new-chat", json={"title": "Regen"})).json()["conversation_id"]
        await c.post("/api/chat", json={"conversation_id": conv, "message": "q1", "stream": False})
        await c.post("/api/chat", json={"conversation_id": conv, "message": "q2", "stream": False})

        resp = await c.post(f"/api/chat/{conv}/regenerate")
        assert resp.status_code == 200
        assert resp.json()["message_count"] == 2

        detail = (await c.get(f"/api/chat/{conv}")).json()["conversation"]
        assert [m["content"] for m in detail["messages"]] == ["q1", "answer"]
    monkeypatch.undo()


@pytest.mark.asyncio
async def test_conversation_is_private_to_owner():
    async def owner() -> UserProfile:
        return UserProfile(uid="owner-1", email="o@test.com")

    async def intruder() -> UserProfile:
        return UserProfile(uid="intruder-1", email="i@test.com")

    app.dependency_overrides[get_current_user] = owner
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            conv = (await c.post("/api/new-chat", json={"title": "Secret"})).json()[
                "conversation_id"
            ]

        # Second user must not be able to read or modify it.
        app.dependency_overrides[get_current_user] = intruder
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            assert (await c.get(f"/api/chat/{conv}")).status_code == 404
            assert (await c.delete(f"/api/chat/{conv}")).status_code == 404
            assert (await c.post(f"/api/chat/{conv}/regenerate")).status_code == 404
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_profile_endpoints(client):
    async with client as c:
        profile = (await c.get("/api/profile")).json()["user"]
        assert profile["uid"] == "e2e-user"

        synced = (await c.post("/api/profile/sync")).json()["user"]
        assert synced["email"] == "e2e@test.com"


@pytest.mark.asyncio
async def test_delete_all_and_export(client):
    async with client as c:
        conv = (await c.post("/api/new-chat", json={"title": "Data"})).json()["conversation_id"]
        assert len((await c.get("/api/chat-history")).json()["conversations"]) >= 1

        exported = (await c.get("/api/profile/export")).json()
        assert exported["user"]["uid"] == "e2e-user"
        assert conv in [x["id"] for x in exported["conversations"]]

        deleted = (await c.delete("/api/profile/chats")).json()
        assert deleted["deleted_count"] >= 1
        assert (await c.get("/api/chat-history")).json()["conversations"] == []


@pytest.mark.asyncio
async def test_feedback_and_validation(client):
    async with client as c:
        fb = await c.post(
            "/api/feedback",
            json={"conversation_id": "c1", "message_id": "m1", "rating": 5, "comment": "Nice"},
        )
        assert fb.status_code == 200
        assert fb.json()["success"] is True

        # Empty message rejected by validation.
        bad = await c.post(
            "/api/chat", json={"conversation_id": "c1", "message": "", "stream": False}
        )
        assert bad.status_code == 422

        # Invalid rating rejected.
        bad_fb = await c.post(
            "/api/feedback",
            json={"conversation_id": "c1", "message_id": "m1", "rating": 9},
        )
        assert bad_fb.status_code == 422
