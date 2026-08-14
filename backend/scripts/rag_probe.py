"""
RAG retrieval probe — run realistic user queries through the retriever and
print which documents come back with their relevance scores.

Usage:
    python scripts/rag_probe.py [query ...]
    (with no queries, runs the built-in probe set)

This is a manual QA tool, not part of the pytest suite.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.rag.loader import warm_knowledge_base
from app.rag.retriever import retrieve

PROBE_QUERIES = [
    "how do I approach sliding window problems",
    "explain two sum",
    "what's the difference between DFS and BFS",
    "big O of merge sort",
    "when should I use dynamic programming",
    "walk me through a backtracking solution",
    "binary search on a sorted array",
    "why does a hash map give me O(1) lookups",
    "how do I solve valid parentheses",
    "topological sort cycle detection",
    "what is the space complexity of recursion",
]


def run(query: str) -> None:
    print(f"\n{'=' * 72}\nQUERY: {query!r}")
    result = retrieve(query, top_k=5)
    if not result.has_context:
        print("  -> NO CONTEXT RETRIEVED (empty result)")
        return
    for chunk in result.chunks:
        meta = chunk.metadata
        title = meta.get("title") or "?"
        category = chunk.source
        number = meta.get("number")
        label = f"{title} (#{number})" if number is not None else title
        preview = chunk.content.splitlines()[0] if chunk.content else ""
        print(f"  [{chunk.score:6.1f}] {category:16s} {label}")
        if preview:
            print(f"         {preview}")


def main() -> None:
    warm_knowledge_base()
    queries = sys.argv[1:] or PROBE_QUERIES
    for query in queries:
        run(query)


if __name__ == "__main__":
    main()
