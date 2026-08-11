"""
AI Agent — the central orchestration layer.

The Agent decides whether to use the LLM alone, the RAG pipeline, both, or
a polite offline reply (for clearly off-topic questions), builds the prompt
via the reusable prompt builder, and returns the response.

The full pipeline is:

    receive message → decide intent (conversation-aware) → (retrieve context)
        → build prompt (system + history + current) → call OpenRouter
        → stream/return response

Refusal policy:
The decision engine only routes a message to the canned OFF_TOPIC reply when
the message *explicitly* hits a non-software keyword. RAG never causes a
rejection — if retrieval finds nothing relevant, the RAG_plus_LLM strategy
transparently falls back to LLM_ONLY and the model answers from knowledge.
"""

from __future__ import annotations

import time
from enum import Enum
from typing import AsyncIterator

from pydantic import BaseModel, Field

from app.core import get_logger
from app.llm import OpenRouterClient
from app.rag import retrieve, RAGResult
from app.schemas import Conversation
from app.services.prompt_builder import build_messages
from app.services.prompt_loader import load_system_prompt
from app.agent.decision_engine import (
    decide,
    prior_technical_topic,
    _enrich_query,
    OFF_TOPIC_MESSAGE,
    Intent,
)

log = get_logger("agent")


# ─── Decision types ──────────────────────────────────────────────

class AgentStrategy(str, Enum):
    """The strategy the agent chose for a particular request."""
    LLM_ONLY = "llm_only"
    RAG_ONLY = "rag_only"
    RAG_PLUS_LLM = "rag_plus_llm"
    OFF_TOPIC = "off_topic"


class AgentResponse(BaseModel):
    """Structured output from the agent."""
    content: str
    strategy: AgentStrategy
    rag_result: RAGResult | None = None
    latency_ms: int = 0
    model: str = ""
    intent: str = ""


# ─── Agent class ──────────────────────────────────────────────────

class Agent:
    """
    Orchestrates the full chat pipeline:

      1. Load system prompt
      2. Decide intent + strategy (aware of the conversation history)
      3. Retrieve context if required
      4. Build the message list (system + history + current message)
      5. Call OpenRouter (or return a canned off-topic reply)
      6. Return the structured AgentResponse
    """

    def __init__(self, llm_client: OpenRouterClient | None = None) -> None:
        self._llm = llm_client or OpenRouterClient()
        self._system_prompt = load_system_prompt()

    # ── Strategy decision ─────────────────────────────────────────

    async def _decide(
        self,
        conversation: Conversation,
        user_message: str,
    ) -> tuple[AgentStrategy, RAGResult | None, str]:
        """
        Classify the message (using conversation history) and resolve the
        strategy.

        Returns ``(strategy, rag_result, intent)``. ``rag_result`` is only
        populated when retrieval is needed and produced relevant context.
        """
        decision = decide(user_message, history=conversation.messages)
        intent = decision.intent.value
        strategy = AgentStrategy(decision.strategy)
        log.info(
            "Agent decision: intent={intent} strategy={strategy} "
            "history_turns={turns}",
            intent=intent,
            strategy=strategy.value,
            turns=len(conversation.messages),
        )

        # Off-topic → polite scoped reply, no model call.
        if strategy == AgentStrategy.OFF_TOPIC:
            log.info("Off-topic refusal returned (no model call)")
            return AgentStrategy.OFF_TOPIC, None, intent

        # RAG-backed strategies → retrieve relevant documents. Retrieval is
        # conversation-aware: the decision may supply an enriched query that
        # prepends the previous topic to short follow-ups.
        if strategy == AgentStrategy.RAG_PLUS_LLM:
            query = decision.retrieval_query or user_message
            rag_result = retrieve(query, top_k=5)
            if not rag_result.has_context and not decision.retrieval_query:
                # A follow-up that carries its own domain keyword (e.g. "ok
                # now explain me the optimal solution") still needs grounding
                # in the previous topic. Enrich with the last technical user
                # message and retry before falling back to LLM_ONLY.
                prior = prior_technical_topic(conversation.messages)
                if prior:
                    enriched = _enrich_query(prior, query)
                    enriched_result = retrieve(enriched, top_k=5)
                    if enriched_result.has_context:
                        log.info(
                            "RAG enrichment: follow-up grounded with prior topic "
                            "'{prior}' query='{q}' kept={n}",
                            prior=_safe(prior),
                            q=_safe(enriched),
                            n=len(enriched_result.chunks),
                        )
                        rag_result = enriched_result
            if rag_result.has_context:
                titles = [c.metadata.get("title") for c in rag_result.chunks[:5]]
                log.info(
                    "Retrieval (strategy={strategy}): {n} chunks from categories "
                    "{categories} docs={titles} query='{q}'",
                    strategy=strategy.value,
                    n=len(rag_result.chunks),
                    categories=[c.source for c in rag_result.chunks[:5]],
                    titles=titles,
                    q=_safe(query),
                )
                return AgentStrategy.RAG_PLUS_LLM, rag_result, intent
            log.info(
                "RAG_plus_LLM: no relevant context found — falling back to "
                "LLM_ONLY (no rejection). query='{query}'",
                query=_safe(query),
            )
            return AgentStrategy.LLM_ONLY, rag_result, intent

        # Everything else → LLM only.
        return AgentStrategy.LLM_ONLY, None, intent

    # ── Off-topic fallback ────────────────────────────────────────

    async def _off_topic_reply(self, intent: str) -> AgentResponse:
        return AgentResponse(
            content=OFF_TOPIC_MESSAGE,
            strategy=AgentStrategy.OFF_TOPIC,
            latency_ms=0,
            intent=intent,
        )

    # ── LeetCode account analysis ───────────────────────────────

    def _account_not_linked_message(self) -> str:
        return (
            "I can analyse your LeetCode progress and recommend the best "
            "problems to solve next — just link your LeetCode username first.\n\n"
            "1. Open **Settings** in the sidebar.\n"
            "2. Under **LeetCode account**, enter your username and press "
            "**Link account**.\n\n"
            "Once linked, ask me things like *\"analyze my solved problems\"* "
            "or *\"what should I solve next?\"*"
        )

    async def _account_data(
        self,
        user_id: str,
    ) -> tuple[str | None, dict, list[dict]]:
        """
        Load a user's LeetCode snapshot + recommendations.

        Returns ``(username, snapshot, recommendations)``. When no account is
        linked, ``username`` is ``None``.
        """
        from app.services.conversation_memory import get_leetcode_username
        from app.leetcode.client import get_leetcode_client
        from app.problems import get_catalog, recommend_next

        username = get_leetcode_username(user_id)
        if not username:
            return None, {}, []

        client = get_leetcode_client()
        snapshot = await client.fetch_user_snapshot(username)

        solved_problems: list[dict] = []
        catalog = get_catalog()
        for submission in snapshot.get("recent_ac") or []:
            problem = catalog.get_by_slug(submission.get("title_slug", ""))
            if problem:
                solved_problems.append(problem.to_dict())
        recommendations = recommend_next(
            [s["title_slug"] for s in snapshot.get("recent_ac") or []],
            solved_problems,
            count=5,
        )
        return username, snapshot, recommendations

    async def _run_account(
        self,
        conversation: Conversation,
        user_message: str,
    ) -> AgentResponse:
        """Full pipeline for "analyse my LeetCode account" requests."""
        start = time.perf_counter()
        try:
            username, snapshot, recommendations = await self._account_data(conversation.user_id)
        except Exception as exc:
            log.warning("LeetCode account lookup failed: {exc}", exc=exc)
            return AgentResponse(
                content=(
                    "I couldn't reach LeetCode to look at your account right "
                    "now. Please try again in a moment."
                ),
                strategy=AgentStrategy.LLM_ONLY,
                latency_ms=0,
                intent=Intent.LEETCODE_ACCOUNT.value,
            )

        if not username:
            return AgentResponse(
                content=self._account_not_linked_message(),
                strategy=AgentStrategy.LLM_ONLY,
                latency_ms=0,
                intent=Intent.LEETCODE_ACCOUNT.value,
            )

        from app.services.leetcode_context import build_account_context

        account_context = build_account_context(username, snapshot, recommendations)

        # System prompt + injected account context + conversation + message.
        base = build_messages(self._system_prompt, conversation, user_message, None)
        messages: list[dict[str, str]] = [
            base[0],
            {"role": "system", "content": account_context},
            *base[1:],
        ]

        model = self._llm.model
        log.info(
            "Analysing LeetCode account: user={uid} username='{username}' "
            "solved={solved}",
            uid=conversation.user_id,
            username=username,
            solved=snapshot.get("accepted", {}).get("total", 0),
        )
        content = await self._llm.complete(messages)

        elapsed = int((time.perf_counter() - start) * 1000)
        return AgentResponse(
            content=content,
            strategy=AgentStrategy.LLM_ONLY,
            latency_ms=elapsed,
            model=model,
            intent=Intent.LEETCODE_ACCOUNT.value,
        )

    async def _stream_account(
        self,
        conversation: Conversation,
        user_message: str,
    ) -> AsyncIterator[str]:
        """Streaming variant of ``_run_account``."""
        start = time.perf_counter()
        try:
            username, snapshot, recommendations = await self._account_data(conversation.user_id)
        except Exception as exc:
            log.warning("LeetCode account lookup failed: {exc}", exc=exc)
            yield "I couldn't reach LeetCode to look at your account right now. Please try again in a moment."
            return

        if not username:
            yield self._account_not_linked_message()
            return

        from app.services.leetcode_context import build_account_context

        account_context = build_account_context(username, snapshot, recommendations)
        base = build_messages(self._system_prompt, conversation, user_message, None)
        messages: list[dict[str, str]] = [
            base[0],
            {"role": "system", "content": account_context},
            *base[1:],
        ]

        streamed = 0
        async for chunk in self._llm.stream(messages):
            streamed += len(chunk)
            yield chunk

        elapsed = int((time.perf_counter() - start) * 1000)
        log.info(
            "LeetCode account stream finished in {ms}ms user={uid} chars={chars}",
            ms=elapsed,
            uid=conversation.user_id,
            chars=streamed,
        )

    # ── Non-streaming entry point ────────────────────────────────

    async def run(
        self,
        conversation: Conversation,
        user_message: str,
    ) -> AgentResponse:
        """Execute the full agent pipeline (non-streaming)."""
        start = time.perf_counter()

        strategy, rag_result, intent = await self._decide(conversation, user_message)
        if strategy == AgentStrategy.OFF_TOPIC:
            return await self._off_topic_reply(intent)
        if intent == Intent.LEETCODE_ACCOUNT.value:
            return await self._run_account(conversation, user_message)

        messages = build_messages(self._system_prompt, conversation, user_message, rag_result)
        self._log_prompt(strategy, messages)

        model = self._llm.model
        log.info(
            "Invoking OpenRouter model='{model}' strategy={strategy}",
            model=model,
            strategy=strategy.value,
        )
        content = await self._llm.complete(messages)

        elapsed = int((time.perf_counter() - start) * 1000)
        log.info(
            "Agent completed in {ms}ms strategy={strategy} model='{model}' "
            "content_len={len}",
            ms=elapsed,
            strategy=strategy.value,
            model=model,
            len=len(content),
        )

        return AgentResponse(
            content=content,
            strategy=strategy,
            rag_result=rag_result if rag_result and rag_result.has_context else None,
            latency_ms=elapsed,
            model=model,
            intent=intent,
        )

    # ── Streaming entry point ────────────────────────────────────

    async def run_stream(
        self,
        conversation: Conversation,
        user_message: str,
    ) -> AsyncIterator[str]:
        """Execute the agent pipeline and yield incremental text chunks."""
        start = time.perf_counter()

        strategy, rag_result, intent = await self._decide(conversation, user_message)

        if strategy == AgentStrategy.OFF_TOPIC:
            log.info("Streaming off-topic reply (no model call)")
            yield OFF_TOPIC_MESSAGE
            return

        if intent == Intent.LEETCODE_ACCOUNT.value:
            async for chunk in self._stream_account(conversation, user_message):
                yield chunk
            return

        messages = build_messages(self._system_prompt, conversation, user_message, rag_result)
        self._log_prompt(strategy, messages)

        model = self._llm.model
        streamed = 0
        log.info(
            "Streaming started: model='{model}' strategy={strategy}",
            model=model,
            strategy=strategy.value,
        )
        async for chunk in self._llm.stream(messages):
            streamed += len(chunk)
            yield chunk

        elapsed = int((time.perf_counter() - start) * 1000)
        log.info(
            "Stream finished in {ms}ms strategy={strategy} model={model} "
            "chars={chars} status=done",
            ms=elapsed,
            strategy=strategy.value,
            model=model,
            chars=streamed,
        )

    def _log_prompt(self, strategy: AgentStrategy, messages: list[dict[str, str]]) -> None:
        """Log prompt size without logging any private user content."""
        total = sum(len(m["content"]) for m in messages)
        system_len = len(messages[0]["content"]) if messages else 0
        log.info(
            "Prompt size: {chars} chars (system={sys}, {n} messages), strategy={strategy}",
            chars=total,
            sys=system_len,
            n=len(messages),
            strategy=strategy.value,
        )


def _safe(text: str) -> str:
    """Trim long strings for log lines."""
    return text if len(text) <= 120 else text[:117] + "..."