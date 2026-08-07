"""
Tests for the JSON knowledge-base loader and retrieval engine.
"""

import pytest

from app.rag.loader import KnowledgeBase, normalize_document
from app.rag.retriever import retrieve, RAGResult


@pytest.fixture(scope="module")
def kb():
    return KnowledgeBase()


def test_knowledge_base_loads_seed_data(kb):
    docs = kb.load()
    assert len(docs) > 0
    assert kb.stats.get("leetcode", 0) >= 8
    assert kb.stats.get("patterns", 0) >= 5


def test_documents_are_normalised(kb):
    docs = kb.load()
    for doc in docs:
        assert doc.title
        assert doc.source in {"leetcode", "patterns", "topics", "algorithms", "complexities", "roadmaps"}
        assert doc.index_text


def test_normalize_document_requires_title():
    doc = normalize_document("leetcode", "x.json", {"description": "no title here"})
    assert doc is None


def test_normalize_document_extracts_fields():
    doc = normalize_document(
        "leetcode",
        "x.json",
        {
            "number": 5,
            "title": "Sample Problem",
            "difficulty": "Medium",
            "tags": ["Array", "Hash Table"],
            "pattern": "Two Pointers",
            "description": "Some body.",
            "hints": ["hint one"],
        },
    )
    assert doc is not None
    assert doc.number == 5
    assert doc.difficulty == "Medium"
    assert doc.tags == ["Array", "Hash Table"]
    assert doc.pattern == "Two Pointers"
    assert doc.sections["hints"] == ["hint one"]


def test_retrieve_by_problem_number(kb):
    result = retrieve("problem number 1")
    assert result.has_context
    top = result.chunks[0]
    assert top.metadata.get("number") == 1
    assert top.metadata.get("title") == "Two Sum"


def test_retrieve_by_title_ranks_exact_match_first(kb):
    result = retrieve("two sum")
    assert result.has_context
    assert result.chunks[0].metadata.get("title") == "Two Sum"
    # Scores should be ordered descending.
    scores = [c.score for c in result.chunks]
    assert scores == sorted(scores, reverse=True)


def test_retrieve_empty_query_returns_empty(kb):
    result = retrieve("", top_k=3)
    assert isinstance(result, RAGResult)
    assert not result.has_context


def test_retrieve_unrelated_returns_empty(kb):
    result = retrieve("what is the meaning of life", top_k=3)
    assert not result.has_context


def test_retrieve_case_insensitive(kb):
    result = retrieve("SLIDING WINDOW")
    assert result.has_context
    assert result.chunks[0].metadata.get("title") == "Sliding Window"
