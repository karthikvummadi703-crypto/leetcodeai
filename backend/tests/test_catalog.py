"""
Tests for the LeetCode problem catalog.
"""

from app.problems import get_catalog, search_problems


def test_catalog_loaded():
    catalog = get_catalog()
    assert catalog.total > 3000
    assert all(isinstance(p.number, int) for p in catalog.problems)


def test_get_by_number():
    catalog = get_catalog()
    problem = catalog.get_by_number(1)
    assert problem is not None
    assert problem.title == "Two Sum"
    assert problem.title_slug == "two-sum"
    assert problem.difficulty == "Easy"
    assert "Array" in problem.topics


def test_get_by_slug():
    catalog = get_catalog()
    problem = catalog.get_by_slug("reverse-linked-list")
    assert problem is not None
    assert problem.title == "Reverse Linked List"


def test_get_by_title_fuzzy():
    catalog = get_catalog()
    assert catalog.get_by_title("Two Sum") is not None
    assert catalog.get_by_title("two sum") is not None


def test_search_by_number():
    results = search_problems("206")
    assert results
    assert results[0]["number"] == 206


def test_search_by_title():
    results = search_problems("valid parentheses", limit=5)
    assert results
    assert any("Parentheses" in r["title"] for r in results)


def test_search_by_topic():
    results = search_problems("sliding window", limit=5)
    assert results
    assert all(any("Sliding" in t for t in r["topics"]) for r in results[:2])


def test_search_empty_and_garbage():
    assert search_problems("") == []
    assert search_problems("zzzqqq_nothing") == []
