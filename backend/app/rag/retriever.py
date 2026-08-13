"""
Local retrieval engine (no vector database).

Searches the in-memory JSON knowledge base using lightweight lexical
scoring. Each query is tokenised and every document is scored across its
structured fields — number, title, difficulty, tags, pattern, algorithm,
keywords and body text — supporting exact, partial, keyword and
multi-keyword searches in a case-insensitive way.

Returns the best matching documents ordered by relevance.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, Field

from app.core import get_logger
from app.rag.loader import DataDocument, get_knowledge_base

log = get_logger("rag.search")


class RetrievedChunk(BaseModel):
    """A single chunk of retrieved context with its relevance score."""

    content: str = Field(..., description="Human readable context for the document")
    source: str = ""
    score: float = 0.0
    metadata: dict = Field(default_factory=dict)


class RAGResult(BaseModel):
    """Aggregate retrieval result."""

    chunks: list[RetrievedChunk] = Field(default_factory=list)
    query: str = ""
    matched: int = 0

    @property
    def has_context(self) -> bool:
        return len(self.chunks) > 0

    @property
    def combined_context(self) -> str:
        return "\n\n".join(chunk.content for chunk in self.chunks)


# ─── Tokenisation ────────────────────────────────────────────────

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    """Lower-case, strip punctuation and split a string into tokens."""
    if not text:
        return []
    return _TOKEN_RE.findall(text.lower())


# English + domain stop words removed from the query before scoring.
_STOP_WORDS = {
    "a", "an", "the", "of", "for", "and", "or", "with", "to", "in", "on",
    "is", "are", "was", "were", "be", "am", "what", "how", "why", "when",
    "where", "who", "which", "please", "explain", "help", "me", "my", "i",
    "you", "it", "this", "that", "these", "those", "can", "could", "would",
    "should", "want", "need", "tell", "question", "related", "like", "stuck",
    "step", "by", "into", "does", "do", "get", "got", "give", "given",
}


# ─── Scoring ─────────────────────────────────────────────────────

# Field weights — structured matches rank far above bare body keywords.
W_NUMBER = 120      # exact problem number
W_TITLE_EXACT = 90  # whole indexed title contains the query phrase
W_TITLE_TOKEN = 45  # query token matches a title token
W_PATTERN = 35      # query token matches the pattern name
W_ALGORITHM = 35    # query token matches the algorithm name
W_TAG = 30          # query token matches a tag
W_DIFFICULTY = 12   # query token matches the difficulty label
W_BODY = 4          # query token appears anywhere in the body


def _score_doc(doc: DataDocument, terms: list[str]) -> float:
    """Score a document against a list of parsed query terms."""
    if not terms:
        return 0.0

    # Exact problem-number match is an immediate, dominant signal.
    if doc.number is not None and str(doc.number) in terms:
        return 1000.0

    # Whole-title phrase match.
    title_phrase = doc.title.lower().strip()
    if len(terms) > 1 and title_phrase in " ".join(terms):
        return 900.0

    title_tokens = set(tokenize(doc.title))
    pattern_tokens = set(tokenize(doc.pattern or ""))
    algorithm_tokens = set(tokenize(doc.algorithm or ""))
    tag_tokens = {t for tag in doc.tags for t in tokenize(tag)}
    difficulty_tokens = set(tokenize(doc.difficulty or ""))
    index_tokens = set(doc.index_text.split())

    score = 0.0
    matched: set[str] = set()

    for term in terms:
        if term in title_tokens:
            score += W_TITLE_TOKEN
            matched.add(term)
        if term in pattern_tokens:
            score += W_PATTERN
            matched.add(term)
        if term in algorithm_tokens:
            score += W_ALGORITHM
            matched.add(term)
        if term in tag_tokens:
            score += W_TAG
            matched.add(term)
        if term in difficulty_tokens:
            score += W_DIFFICULTY
            matched.add(term)
        if term in index_tokens:
            score += W_BODY
            matched.add(term)

    if not matched:
        return 0.0

    # Reward how much of the query was actually matched (precision).
    coverage = len(matched) / len(terms)
    score *= 0.35 + 0.65 * coverage
    return round(score, 2)


def _query_terms(query: str) -> list[str]:
    """Tokenise a query and drop stop words."""
    return [t for t in tokenize(query) if t not in _STOP_WORDS]


# ─── Retrieval ───────────────────────────────────────────────────

def _format_metadata(doc: DataDocument) -> dict:
    """Build a small, safe metadata dict for a document."""
    return {
        "doc_id": doc.doc_id,
        "title": doc.title,
        "category": doc.source,
        "difficulty": doc.difficulty,
        "number": doc.number,
        "tags": doc.tags,
        "pattern": doc.pattern,
        "algorithm": doc.algorithm,
    }


def retrieve(
    query: str,
    top_k: int = 5,
    min_score: float = 10.0,
) -> RAGResult:
    """
    Retrieve the most relevant knowledge-base documents for ``query``.

    Performs exact, partial, keyword and multi-keyword matching, ranks the
    results by relevance and returns the best ``top_k`` matches. Documents
    scoring below a relevance threshold are discarded so the caller can fall
    back to pure-LLM mode when nothing relevant is found.
    """
    terms = _query_terms(query)

    if not terms:
        log.debug("Query produced no search terms", query_len=len(query))
        return RAGResult(query=query, chunks=[])

    # Threshold scales gently with the number of query terms so a lone
    # keyword needs a strong (title/tag/pattern) match before it counts.
    threshold = max(min_score, W_BODY * len(terms))

    scored: list[tuple[float, DataDocument]] = []
    for doc in get_knowledge_base().documents:
        score = _score_doc(doc, terms)
        if score > 0:
            scored.append((score, doc))

    if not scored:
        log.info("Retrieval: no matches for query (terms={n})", n=len(terms))
        return RAGResult(query=query, chunks=[])

    # Rank by relevance (ties broken by shorter/index order).
    scored.sort(key=lambda item: item[0], reverse=True)

    chunks: list[RetrievedChunk] = []
    for score, doc in scored:
        if score < threshold or len(chunks) >= top_k:
            if score < threshold:
                break
            continue
        from app.rag.context_builder import format_document

        content = format_document(doc)
        chunks.append(
            RetrievedChunk(
                content=content,
                source=doc.source,
                score=score,
                metadata=_format_metadata(doc),
            )
        )

    # Fall back/supplement with search from the full LeetCode catalog of 4,000+ problems.
    from app.problems import get_catalog
    catalog = get_catalog()
    catalog_matches = catalog.search(query, limit=top_k)
    has_digit = any(t.isdigit() for t in terms)
    for problem in catalog_matches:
        if len(chunks) >= top_k:
            break
        # Avoid duplicate if already fetched from local RAG documents
        if any(c.metadata.get("number") == problem.number for c in chunks):
            continue
        
        # Avoid generic false positives by requiring a problem number
        # or at least 2 matching tokens in the problem title.
        title_tokens = set(tokenize(problem.title))
        matched_title_tokens = title_tokens.intersection(terms)
        if not (has_digit or len(matched_title_tokens) >= 2):
            continue

        acceptance_str = f"{problem.acceptance * 100:.1f}%" if problem.acceptance is not None else "—"
        content = (
            f"### LeetCode Catalog Entry: {problem.title} (#{problem.number})\n"
            f"Difficulty: {problem.difficulty}\n"
            f"Topics: {', '.join(problem.topics)}\n"
            f"URL: {problem.url}\n"
            f"Acceptance: {acceptance_str}\n"
            f"This is a verified problem in the LeetCode catalog. Answer the user's question about it using your pre-trained knowledge."
        )
        chunks.append(
            RetrievedChunk(
                content=content,
                source="leetcode_catalog",
                score=95.0,
                metadata={
                    "doc_id": f"catalog_{problem.number}",
                    "title": problem.title,
                    "category": "leetcode_catalog",
                    "difficulty": problem.difficulty,
                    "number": problem.number,
                    "tags": problem.topics,
                }
            )
        )

    log.info(
        "Retrieval: {matched} matches, kept {kept} for '{q}' (threshold={thr})",
        matched=len(scored),
        kept=len(chunks),
        q=query[:60],
        thr=round(threshold, 2),
    )
    return RAGResult(query=query, chunks=chunks, matched=len(scored))