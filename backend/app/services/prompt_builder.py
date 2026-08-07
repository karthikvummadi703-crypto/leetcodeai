"""
Reusable prompt builder.

Assembles the exact message list sent to OpenRouter for every request:

    1. System prompt        — mentor-style instructions (+ optional RAG context)
    2. Conversation history — previous turns (kept within token limits)
    3. Current user message — the new question

Retrieved data is converted into clean readable context (never raw JSON)
before being injected.
"""

from __future__ import annotations

from app.core import get_logger
from app.rag.retriever import RAGResult
from app.schemas import Conversation

log = get_logger("prompt_builder")

MAX_HISTORY_TURNS = 20        # last N user/assistant turns included
MAX_CONTEXT_CHARS = 8_000     # cap for the RAG context block


def build_context_block(rag_result: RAGResult | None) -> str:
    """
    Render retrieved documents as a clean, deduplicated context block.

    The retriever already formats each document as readable text
    (``chunk.content``); this joins them, dropping duplicate titles, and
    caps the total size. Returns an empty string when there is nothing
    relevant to inject.
    """
    if rag_result is None or not rag_result.has_context:
        return ""

    seen: set[tuple[str, int | None]] = set()
    sections: list[str] = []
    used = 0

    for chunk in rag_result.chunks:
        title = (chunk.metadata.get("title") or "").strip().lower()
        number = chunk.metadata.get("number")
        key = (title, number)
        if key in seen:
            continue
        seen.add(key)

        text = chunk.content.strip()
        if not text:
            continue
        if used + len(text) + 2 > MAX_CONTEXT_CHARS:
            break
        sections.append(text)
        used += len(text) + 2

    return "\n\n".join(sections)


def build_messages(
    system_prompt: str,
    conversation: Conversation,
    user_message: str,
    rag_result: RAGResult | None = None,
    *,
    max_history_turns: int = MAX_HISTORY_TURNS,
) -> list[dict[str, str]]:
    """
    Build the full OpenRouter message list.

    Structure:
      [system]  system prompt + optional retrieved context
      [history] previous conversation turns (truncated)
      [user]    the new user question
    """
    system_content = system_prompt

    context = build_context_block(rag_result)
    if context:
        system_content += (
            "\n\n## Retrieved Context\n"
            "The following verified information was retrieved from the local "
            "knowledge base. Use it to ground your answer, but treat it as "
            "reference material — stay in your mentor role.\n\n"
            f"{context}"
        )

    messages: list[dict[str, str]] = [{"role": "system", "content": system_content}]

    # Conversation history — last N turns to stay within context limits.
    history = conversation.messages[-max_history_turns:]
    for msg in history:
        if msg.role.value in {"user", "assistant", "system"}:
            messages.append({"role": msg.role.value, "content": msg.content})

    messages.append({"role": "user", "content": user_message})

    total_chars = sum(len(m["content"]) for m in messages)
    log.debug(
        "Prompt built: {turns} history turns, {chars} chars (context={ctx} chars)",
        turns=len(history),
        chars=total_chars,
        ctx=len(context),
    )
    return messages