"""
Integration tests for the chat endpoint and the agent orchestration.
"""

import orjson
import pytest
from httpx import AsyncClient, ASGITransport

from main import app
from app.agent import Agent
from app.agent.decision_engine import OFF_TOPIC_MESSAGE
from app.schemas import Conversation, Message, MessageRole


# ── Auth protection ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_chat_requires_authentication():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/chat",
            json={"conversation_id": "abc", "message": "hello", "stream": False},
        )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_new_chat_requires_authentication():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/new-chat", json={"title": "Hi"})
    assert response.status_code == 401


# ── Agent with a stubbed LLM ─────────────────────────────────────

class StubLLM:
    """Fake OpenRouter client that records the prompt and returns canned text."""

    def __init__(self) -> None:
        self._model = "stub-model"
        self.last_messages: list[dict[str, str]] | None = None
        self.call_count = 0

    @property
    def model(self) -> str:
        return self._model

    async def complete(self, messages: list[dict[str, str]]) -> str:
        self.call_count += 1
        self.last_messages = messages
        return "Here is a mentor-style answer."

    async def stream(self, messages: list[dict[str, str]]):  # pragma: no cover
        self.last_messages = messages
        yield "one"
        yield "two"


def _conversation(turns: int = 0) -> Conversation:
    messages = []
    for i in range(turns):
        messages.append(Message(id=f"u{i}", role=MessageRole.USER, content=f"q{i}"))
        messages.append(Message(id=f"a{i}", role=MessageRole.ASSISTANT, content=f"a{i}"))
    return Conversation(id="conv-1", user_id="u1", messages=messages)


@pytest.mark.asyncio
async def test_agent_off_topic_skips_llm():
    llm = StubLLM()
    agent = Agent(llm_client=llm)

    result = await agent.run(_conversation(), "Who won the football match yesterday?")

    assert result.strategy.value == "off_topic"
    assert result.content == OFF_TOPIC_MESSAGE
    assert llm.call_count == 0


@pytest.mark.asyncio
async def test_agent_rag_plus_llm_uses_context():
    llm = StubLLM()
    agent = Agent(llm_client=llm)

    result = await agent.run(_conversation(), "Explain the Two Sum problem")

    assert result.strategy.value == "rag_plus_llm"
    assert result.content == "Here is a mentor-style answer."
    assert llm.call_count == 1
    assert llm.last_messages is not None
    assert llm.last_messages[0]["role"] == "system"
    assert "Two Sum" in llm.last_messages[0]["content"]
    assert llm.last_messages[-1]["content"] == "Explain the Two Sum problem"


@pytest.mark.asyncio
async def test_agent_includes_history():
    llm = StubLLM()
    agent = Agent(llm_client=llm)

    await agent.run(_conversation(turns=2), "What is the space complexity of a hash table?")

    assert llm.last_messages is not None
    # system + 4 history messages + new user message
    assert len(llm.last_messages) == 6


@pytest.mark.asyncio
async def test_agent_grounds_keyword_followup_in_prior_topic():
    llm = StubLLM()
    agent = Agent(llm_client=llm)

    # A follow-up that contains its own domain keyword ("optimal solution")
    # must still be grounded in the previous topic's documents.
    history = [
        Message(id="u0", role=MessageRole.USER, content="What is the Two Sum problem?"),
        Message(id="a0", role=MessageRole.ASSISTANT, content="It asks to find two numbers that sum to target."),
    ]
    conv = Conversation(id="conv-1", user_id="u1", messages=history)

    result = await agent.run(conv, "ok now explain me the optimal solution")

    assert result.strategy.value == "rag_plus_llm"
    assert llm.last_messages is not None
    assert "Two Sum" in llm.last_messages[0]["content"]


@pytest.mark.asyncio
async def test_agent_streaming_off_topic():
    llm = StubLLM()
    agent = Agent(llm_client=llm)

    chunks = [chunk async for chunk in agent.run_stream(_conversation(), "Who won the cricket match yesterday?")]

    assert chunks == [OFF_TOPIC_MESSAGE]
    assert llm.call_count == 0


# ── Streaming endpoint (SSE) ────────────────────────────────────

class StubAgent:
    """Fake agent that streams known chunks, used for endpoint-level tests."""

    async def run_stream(self, conversation, user_message):
        for chunk in ("Hello", " world", "!"):
            yield chunk


@pytest.mark.asyncio
async def test_chat_streaming_emits_json_sse(monkeypatch):
    from app.api import chat as chat_module
    from app.auth import get_current_user
    from app.schemas import UserProfile
    from app.services.conversation_memory import create_conversation

    async def fake_user():
        return UserProfile(uid="test-uid", email="t@t.com")

    conv = create_conversation("test-uid", "Stream Conv")

    # Override auth + agent so no Firebase / network is touched.
    original_agent = chat_module._agent
    chat_module._agent = StubAgent()
    app.dependency_overrides[get_current_user] = fake_user

    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            async with client.stream(
                "POST",
                "/api/chat",
                json={
                    "conversation_id": conv.id,
                    "message": "hello world",
                    "stream": True,
                },
            ) as response:
                body = (await response.aread()).decode("utf-8")

        assert response.status_code == 200
        assert "data: " in body
        assert body.endswith("data: [DONE]\n\n")
        # Every frame before [DONE] must be JSON-encoded so multi-line
        # tokens survive the SSE framing.
        frames = [f for f in body.split("\n\n") if f.startswith("data: ") and "[DONE]" not in f]
        parsed = [orjson.loads(f[6:]) for f in frames]
        assert parsed == [{"chunk": "Hello"}, {"chunk": " world"}, {"chunk": "!"}]
    finally:
        chat_module._agent = original_agent
        app.dependency_overrides.clear()
