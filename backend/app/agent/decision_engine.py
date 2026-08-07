"""
Agent decision engine.

Classifies the user's message into an intent and decides which strategy the
agent should follow:

* DSA / LeetCode / Algorithms  → RAG + OpenRouter
* General programming          → OpenRouter only
* Greeting                     → OpenRouter only
* Explicitly off-topic         → polite scoped reply (no model call)
* Ambiguous                    → RAG + OpenRouter (never rejected by default)

Conversation awareness:

The engine is **conversation aware**. It receives the previous messages of
the current conversation and, when the latest message is a short follow-up
("what is the optimal solution?", "show a dry run", "why HashMap?") that does
not itself contain a topic, it treats it as a *continuation* of the last
technical discussion and keeps the thread on-topic. The retrieval query is
enriched with the previous topic so RAG can still find the relevant documents.

Refusal policy:

A message is only classified OFF_TOPIC when it *explicitly* contains a
non-software keyword (politics, sports, movies, cooking, …). Anything else —
including messages with no detectable signal — is forwarded to the LLM,
which decides how to answer under the mentor system prompt. This guarantees
valid DSA questions (or their follow-ups) are never rejected.

The engine is keyword/rule driven and deliberately modular so additional
classifiers (e.g. intent models, tool routers) can be plugged in later.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from app.core import get_logger
from app.rag import retrieve
from app.schemas import Message, MessageRole

log = get_logger("agent.decision")

OFF_TOPIC_MESSAGE = (
    "I'm LeetCode Guidance AI — your personal Data Structures & Algorithms "
    "mentor. I can help you with LeetCode problems, DSA concepts, algorithms, "
    "complexity analysis, patterns, and interview prep.\n\n"
    "That topic is outside my expertise, but feel free to ask me anything "
    "about coding, data structures, or algorithms!"
)


class Intent(str, Enum):
    """The classified intent of a user message."""

    LEETCODE = "leetcode"
    DSA = "dsa"
    ALGORITHM = "algorithm"
    PROGRAMMING = "programming"
    GREETING = "greeting"
    FOLLOWUP = "follow_up"
    GENERAL = "general"
    OFF_TOPIC = "off_topic"


@dataclass
class Decision:
    """Result of the decision engine."""

    intent: Intent
    strategy: str
    message: str | None = None
    retrieval_query: str = ""


# ─── Keyword dictionaries (extend freely) ───────────────────────

_GREETING_RE = re.compile(
    r"^(hi|hello|hey|yo|hiya|howdy|hola|namaste|good\s?(morning|afternoon|evening|day))\b",
    re.IGNORECASE,
)

_THANKFUL_RE = re.compile(r"^(thanks?|thank you|ty|thx)\b", re.IGNORECASE)

# Terms that strongly indicate LeetCode / problem references.
_LEETCODE_KEYWORDS = {
    "leetcode", "problem", "question", "code", "lc",
    "two sum", "two-sum", "valid parentheses", "sliding window",
    "longest substring", "merge intervals", "k closest", "top k",
    "contains duplicate", "contains-duplicate", "plus one",
    "climbing stairs", "house robber", "coin change", "palindrome",
    "reverse linked", "valid anagram", "group anagrams", "maximum subarray",
    "optimal solution", "optimum solution", "brute force", "brute-force",
    "optimized solution", "optimized approach", "follow up", "follow-up",
    "explain the solution", "dry run", "pseudocode", "pseudo code",
    "code explanation", "explain the code", "debug this", "interview",
    "interview question", "interview prep", "coding pattern", "coding patterns",
    "solution", "solutions",
    # Common problem names — a random LeetCode mention should always be
    # routed to RAG + LLM, never refused as off-topic.
    "jump game", "game of life", "word ladder", "word break", "lru cache",
    "number of islands", "median of two sorted arrays", "merge two sorted lists",
    "linked list cycle", "reverse a linked list", "valid palindrome",
    "longest palindromic", "roman to integer", "integer to roman",
    "3sum", "three sum", "container with most water",
    "product of array except self", "best time to buy", "kth largest",
    "top k frequent", "subsets", "permutations", "combination sum",
    "generate parentheses", "next permutation", "spiral matrix",
    "rotate image", "course schedule", "clone graph", "word search",
    "longest common subsequence", "edit distance", "regular expression",
    "minimum window", "trapping rain water", "longest increasing subsequence",
    "unique paths", "decode ways", "invert binary tree",
    "validate binary search tree", "diameter of binary tree",
    "lowest common ancestor", "binary tree", "binary search tree",
    "subarray", "subsequence", "anagram", "island",
}

# Core DSA vocabulary.
_DSA_KEYWORDS = {
    "array", "arrays", "string", "strings", "hash", "hashmap", "hash table",
    "map", "set", "list", "linked list", "linked-list", "stack", "queue",
    "deque", "heap", "priority queue", "tree", "binary tree", "bst",
    "binary search tree", "trie", "graph", "vertex", "edge", "node",
    "graph traversal", "backtracking", "recursion", "memoization",
    "dynamic programming", "dp", "greedy", "divide and conquer",
    "sliding window", "two pointers", "two-pointers", "binary search",
    "sorting", "sort", "search", "data structure", "data structures",
    "adjacency", "topological", "union find", "disjoint set", "segment tree",
    "bit manipulation", "bitmask", "fenwick", "trie", "b-tree", "avl",
    "red-black", "queue", "monotonic", "prefix sum", "prefix-sum",
    "interval", "intervals", "frequency", "counter", "dictionary",
    "big-o", "big o", "space complexity", "time complexity", "complexity",
    "o(1)", "o(n)", "o(n log n)", "o(log n)", "o(n^2)", "o(n²)",
    "optimization", "optimization", "optimize", "optimised", "optimized",
    "optimal", "optimum", "efficient", "efficiency", "brute force",
    "brute-force", "naive", "naïve", "intuition", "approach",
    "edge case", "edge cases", "edge-case", "optimization technique",
    "system design", "system-design", "complexity analysis",
    "interview question", "interview", "coding", "programming",
    "data structures", "performance", "time complexity", "space complexity",
}

# Algorithm-name vocabulary.
_ALGORITHM_KEYWORDS = {
    "algorithm", "algorithms", "binary search", "merge sort", "quick sort",
    "insertion sort", "selection sort", "heap sort", "bubble sort",
    "radix sort", "counting sort", "topological sort", "kruskal",
    "prim", "dijkstra", "bellman-ford", "floyd-warshall", "bfs", "dfs",
    "breadth-first", "depth-first", "binary search", "divide and conquer",
    "two pointers", "two-pointers", "sliding window", "fast and slow",
    "monotonic stack", "monotonic queue", "memoization", "recursion",
    "backtracking", "dynamic programming", "greedy", "kadane",
    "binary exponentiation", "modular exponentiation", "sieve",
    "eratosthenes", "euclid", "fast exponentiation", "binary lifting",
    "tarjan", "kosaraju", "a*", "a star", "floyd", "sorting", "search",
    "greedy", "recursion", "backtracking", "memoization", "dfs", "bfs",
    "optimal solution", "brute force", "brute-force", "optimization",
    "dry run", "pseudocode", "pseudo code", "complexity", "intuition",
    "two sum", "hash map", "hashmap", "hash table", "prefix sum",
    "union find", "bit manipulation", "sliding window", "two pointer",
    "two-pointer", "dynamic programming", "dijkstra",
}

# Programming (non-DSA) vocabulary.
_PROGRAMMING_KEYWORDS = {
    "python", "javascript", "typescript", "java", "c++", "c#", "golang", "go",
    "rust", "ruby", "php", "swift", "kotlin", "sql", "html", "css", "react",
    "vue", "angular", "node", "npm", "git", "docker", "kubernetes", "api",
    "rest", "database", "sqlite", "postgres", "mysql", "mongodb", "server",
    "client", "framework", "library", "package", "function", "class",
    "variable", "loop", "if statement", "bug", "error", "debug", "test",
    "unit test", "deploy", "compile", "compile error", "runtime error",
    "exception", "exception handling", "concurrency", "thread", "async",
    "await", "callback", "promise", "regex", "regexp", "parsing", "json",
    "http", "frontend", "backend", "full stack", "web", "mobile", "app",
    "write code", "code review", "refactor", "syntax", "print",
    "hello world", "environment", "pip", "install", "ide", "vim",
    "command line", "terminal", "script", "automation", "oop",
    "object oriented", "inheritance", "polymorphism", "interface",
    "code", "coding", "programming", "developer", "software", "engineering",
}

# Terms that strongly indicate an off-topic / non-technical question.
# These are *explicit* refusals only — and they are deliberately kept to
# unambiguous non-software domains. Generic words that also appear in real
# LeetCode / system-design topics (game, name, history, story, news,
# shopping, travel, relationship, birthday, joke, ...) must NOT be here,
# otherwise questions like "Jump Game" or "browser history" get wrongly
# refused. Anything not matching this list is forwarded to the LLM.
_OFF_TOPIC_KEYWORDS = {
    "sports", "cricket", "football", "soccer", "tennis",
    "weather", "forecast",
    "politics", "political", "election", "president", "government", "senate",
    "horoscope", "astrology",
    "religion",
    "poem", "poetry",
    "cooking",
}


# ─── Decision logic ─────────────────────────────────────────────

def _normalize(query: str) -> str:
    return " ".join(query.lower().split())


# Cache compiled patterns so decision calls stay fast.
_KEYWORD_CACHE: dict[tuple[tuple[str, ...], ...], list[re.Pattern[str]]] = {}


def _keyword_patterns(keywords: set[str]) -> list[re.Pattern[str]]:
    """Compile word-boundary regexes for a keyword set (cached)."""
    key = (tuple(sorted(keywords)),)
    patterns = _KEYWORD_CACHE.get(key)
    if patterns is None:
        patterns = [re.compile(rf"\b{re.escape(kw)}\b") for kw in sorted(keywords)]
        _KEYWORD_CACHE[key] = patterns
    return patterns


def _contains_any(query: str, keywords: set[str]) -> bool:
    """
    Return True if any keyword appears in the query.

    Keywords are matched on word boundaries so short terms like 'ide' or
    'go' cannot accidentally match inside larger words ('president',
    'google'). Phrase keywords such as 'two sum' match as whole phrases.
    """
    for pattern in _keyword_patterns(keywords):
        if pattern.search(query):
            return True
    return False


def _prior_user_topic(messages: list[Message] | None) -> str:
    """
    Return the normalized content of the *last* user message in the history.

    Used for conversation awareness: a short follow-up is resolved against
    the most recent user question instead of being interpreted standalone.
    """
    if not messages:
        return ""
    for msg in reversed(messages):
        role = getattr(msg, "role", None)
        role_value = role.value if hasattr(role, "value") else role
        if role_value == MessageRole.USER.value:
            return _normalize(msg.content)
    return ""


def _is_technical(text: str) -> bool:
    """Whether a prior message belongs to a coding / DSA discussion."""
    return bool(
        _contains_any(text, _LEETCODE_KEYWORDS)
        or _contains_any(text, _DSA_KEYWORDS)
        or _contains_any(text, _ALGORITHM_KEYWORDS)
        or _contains_any(text, _PROGRAMMING_KEYWORDS)
    )


def _enrich_query(prior_topic: str, current: str) -> str:
    """Enrich a short follow-up with the previous topic for retrieval."""
    if prior_topic:
        return f"{prior_topic} {current}".strip()
    return current


def prior_technical_topic(messages: list[Message] | None) -> str:
    """
    Return the normalized content of the last user message when it belongs
    to a technical (coding / DSA) discussion, otherwise ``""``.

    Public helper used by the agent to ground follow-up retrieval in the
    previous topic even when the follow-up itself carries a domain keyword
    (e.g. "ok now explain me the optimal solution").
    """
    prior = _prior_user_topic(messages)
    if prior and _is_technical(prior):
        return prior
    return ""


def _decision_rag(intent: Intent, retrieval_query: str = "") -> Decision:
    if retrieval_query:
        log.info(
            "Decision: {intent} intent -> rag_plus_llm (retrieval enriched)",
            intent=intent.value,
        )
    else:
        log.info("Decision: {intent} intent -> rag_plus_llm", intent=intent.value)
    return Decision(intent, "rag_plus_llm", retrieval_query=retrieval_query)


def decide(query: str, history: list[Message] | None = None) -> Decision:
    """
    Classify ``query`` (with optional prior conversation ``history``) and
    return the strategy the agent should follow.
    """
    normalized = _normalize(query)
    prior_topic = _prior_user_topic(history)
    prior_technical = bool(prior_topic) and _is_technical(prior_topic)

    # 1. Greetings & thanks → friendly LLM-only reply.
    if _GREETING_RE.match(normalized) or _THANKFUL_RE.match(normalized):
        log.info("Decision: greeting intent -> llm_only")
        return Decision(Intent.GREETING, "llm_only")

    # 2. LeetCode / DSA / Algorithms → RAG + LLM.
    if _contains_any(normalized, _LEETCODE_KEYWORDS):
        return _decision_rag(Intent.LEETCODE)
    if _contains_any(normalized, _DSA_KEYWORDS):
        return _decision_rag(Intent.DSA)
    if _contains_any(normalized, _ALGORITHM_KEYWORDS):
        return _decision_rag(Intent.ALGORITHM)

    # 3. General programming → LLM only (still scoped by the system prompt).
    if _contains_any(normalized, _PROGRAMMING_KEYWORDS):
        log.info("Decision: programming intent -> llm_only")
        return Decision(Intent.PROGRAMMING, "llm_only")

    # 4. Explicitly off-topic → polite scoped reply.
    if _contains_any(normalized, _OFF_TOPIC_KEYWORDS):
        log.info("Decision: off-topic intent -> off_topic")
        return Decision(Intent.OFF_TOPIC, "off_topic", message=OFF_TOPIC_MESSAGE)

    # 5. Conversation follow-up — the current message is ambiguous but the
    #    previous discussion was technical. Treat it as a continuation of that
    #    thread and enrich the retrieval query with the prior topic, so
    #    "explain the optimal solution" still retrieves the Two Sum documents.
    if prior_technical:
        log.info(
            "Decision: follow-up detected (prior='{prior}') -> rag_plus_llm",
            prior=prior_topic[:60],
        )
        return _decision_rag(Intent.FOLLOWUP, _enrich_query(prior_topic, normalized))

    # 6. Ambiguous first question → let retrieval decide. A strong KB match
    #    makes it a DSA question.
    rag_result = retrieve(normalized, top_k=1)
    if rag_result.has_context:
        log.info("Decision: retrieval-backed dsa intent -> rag_plus_llm")
        return _decision_rag(Intent.DSA)

    # 7. Default — never reject. Forward to the LLM; the agent transparently
    #    degrades to LLM_ONLY if retrieval finds nothing. The mentor system
    #    prompt decides what is actually answerable.
    log.info(
        "Decision: no domain signal — defaulting to rag_plus_llm (LLM may "
        "still answer or politely decline) to avoid false rejections"
    )
    return _decision_rag(Intent.GENERAL)
